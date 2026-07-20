import json

import blf
import bpy
import gpu

from ..utils.public import debug_print
from ..utils import get_region_height, get_region_width
from ..utils.public import PublicOperator, get_pref, PublicMouseModal
from ..utils.public_gpu import PublicGpu
from ..utils.expression import literal_to_dict


class State:
    show_region_hud = None

    def start_hud(self, context):
        space = getattr(context, "space_data", None)
        if space is None:
            self.show_region_hud = None
            return
        self.show_region_hud = space.show_region_hud
        space.show_region_hud = False

    def restore_hud(self, context):
        if self.show_region_hud is None:
            return
        space = getattr(context, "space_data", None)
        if space is None:
            return
        space.show_region_hud = self.show_region_hud


class KeymapTips(PublicGpu):
    __temp_draw__ = None

    @property
    def tips_text(self):
        texts = []
        element = self.element
        for e in element.modal_events:
            texts.append({"tool": e.property_name, "key": e.event_text})
        from bpy.app.translations import pgettext_iface as translate
        texts.append({"doc": translate(element.name, 'Operator')})
        return texts

    def draw_keymap_tips(self):
        texts = self.tips_text
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)
        from bpy.app.translations import pgettext_iface as translate
        context = bpy.context

        font_id = 0
        font_size = 1.2
        column_space_size = 10 * font_size
        key_row_space = 100 * font_size

        blf.size(font_id, 12 * font_size)
        blf.color(font_id, 1, 1, 1, 1)

        offset_x, offset_y = 10, 30

        asset_shelf = get_region_height(context, "ASSET_SHELF")
        asset_shelf_header = get_region_height(context, "ASSET_SHELF_HEADER")

        toolbar_width = get_region_width(context)

        x1 = toolbar_width + offset_x
        y1 = offset_y + asset_shelf + asset_shelf_header

        y2 = y1

        max_width = 0
        with gpu.matrix.push_pop():
            gpu.matrix.translate((x1, y1))
            for index, item in enumerate(texts):
                if "doc" in item:
                    blf.position(font_id, 0, 0, 0)
                    text = translate(item["doc"])
                    blf.draw(font_id, text)
                    width, height = blf.dimensions(font_id, text)

                    y = height + column_space_size
                    y2 += y
                    gpu.matrix.translate((0, y))
                    if max_width < width:
                        max_width = width
                else:
                    tool = translate(item["tool"])
                    key = translate(item["key"])
                    # draw tool
                    blf.position(font_id, 0, 0, 0)
                    blf.draw(font_id, tool)
                    tw, th = blf.dimensions(font_id, tool)

                    # draw key
                    off = key_row_space * font_size
                    blf.position(font_id, off, 0, 0)
                    blf.draw(font_id, key)
                    kw, kh = blf.dimensions(font_id, tool)

                    height = max(th, kh) + column_space_size
                    gpu.matrix.translate((0, height))
                    y2 += height
                    width = tw + kw + off
                    if max_width < width:
                        max_width = width

    def register_draw(self):
        try:
            self.__temp_draw__ = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_keymap_tips, (), "WINDOW", 'POST_PIXEL')
        except Exception as e:
            self.__temp_draw__ = None
            debug_print(e.args, key='modal')
            import traceback
            traceback.print_exc()
            traceback.print_stack()

    def unregister_draw(self):
        if self.__temp_draw__ is None:
            return
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self.__temp_draw__, "WINDOW")
        except (ValueError, RuntimeError, TypeError):
            ...
        self.__temp_draw__ = None
        self.tag_redraw()


class ElementModal(PublicOperator, State, PublicMouseModal, KeymapTips):
    bl_idname = 'wm.gesture_element_modal_event'
    bl_label = 'Element Modal'
    bl_description = 'Run a modal operator element and map events to its properties'
    # UNDO on the wrapper: the target operator runs exactly once on confirm and
    # folds into this operator's single undo step.
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    operator_properties: dict

    @classmethod
    def poll(cls, context):
        gesture = getattr(context, "gesture", None)
        element = getattr(context, "element", None)
        if not gesture or not element:
            cls.poll_message_set("Modal operator requires gesture and element context")
            return False
        if not element.operator_is_modal:
            cls.poll_message_set("Element is not a modal operator")
            return False
        return True

    def invoke(self, context, event):
        self.init_invoke(event)
        self.gesture = getattr(context, "gesture", None)
        self.element = getattr(context, "element", None)
        props = getattr(self.element, "last_properties", None) or {}
        if isinstance(props, str):
            props = literal_to_dict(props) or {}
        # Mutable working copy updated by modal event handlers.
        self.operator_properties = dict(props)
        debug_print(self.bl_idname, self.gesture, self.element, self.operator_properties, key='modal')

        # Only collect property values during the drag. Re-running arbitrary
        # operators cannot be rolled back safely across all Blender data types.
        # The target operator is executed exactly once, on confirmation.
        self.start_hud(context)
        self.start_mouse(event)
        self.register_draw()
        self.update_header_text(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _props_dict(self) -> dict:
        props = self.operator_properties
        if props is None:
            return {}
        if isinstance(props, str):
            return literal_to_dict(props) or {}
        return props

    def _run_target_operator(self):
        """EXEC the target once with collected props; undo folds into the wrapper."""
        func = self.element.operator_func
        if func is None:
            return RuntimeError("operator not found")
        prop = self._props_dict()
        try:
            func('EXEC_DEFAULT', False, **prop)
            return None
        except Exception as e:
            debug_print('_run_target_operator ERROR', e, key='modal')
            return e

    def modal(self, context, event):
        self.init_modal(event)
        pref = get_pref()
        if event.type == "LEFTMOUSE" and event.value == "PRESS":  # Confirm
            error = self._run_target_operator()
            if error is not None:
                self.report({'ERROR'}, str(error))
                return self.exit(context, cancelled=True)
            self.finished(context)
            return self.exit(context)

        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if event.value == "PRESS" and (self.is_right_mouse or event.type == "ESC"):
            return self.exit(context, cancelled=True)
        if event.type not in ("TIMER_REPORT",):
            element = self.element
            if element.run_element_modal_event(self, context, event):
                self.update_header_text(context)
                return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def update_header_text(self, context):
        context.area.header_text_set(self.element.get_header_text(self._props_dict()))

    def exit(self, context, *, cancelled=False):
        if context.area is not None:
            context.area.header_text_set(None)
        self.restore_hud(context)
        self.unregister_draw()
        super().exit()
        return {"CANCELLED" if cancelled else "FINISHED"}

    def cancel(self, context):
        self.exit(context, cancelled=True)

    def finished(self, context):
        """On finish, save changed properties for next operator invoke."""
        self.element.last_modal_operator_property = json.dumps(self._props_dict())
