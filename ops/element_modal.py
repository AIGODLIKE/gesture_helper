import json
import time

import blf
import bmesh
import bpy
import gpu

from ..utils.public import debug_print
from ..utils import get_region_height, get_region_width
from ..utils.public import PublicOperator, get_pref, PublicMouseModal
from ..utils.public_gpu import PublicGpu
from ..utils.adapter import operator_setattr, operator_getattr
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

        x2 = x1
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
    # No UNDO on the wrapper — preview uses snapshot restore, not ed.undo / undo_redo.
    bl_options = {'REGISTER', 'GRAB_CURSOR', 'BLOCKING'}

    operator_properties: dict
    last_running_time = 0

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

        # One undo checkpoint for Ctrl+Z after confirm; preview itself never uses ed.undo.
        if bpy.ops.ed.undo_push.poll():
            bpy.ops.ed.undo_push(message="Gesture Element Modal")

        operator_setattr(self, '_applied', False)
        self._capture_baseline(context)
        err = self._run_target_operator()
        if err is None:
            operator_setattr(self, '_applied', True)

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

    def _capture_baseline(self, context) -> None:
        """Snapshot edit meshes + object names before the first apply."""
        operator_setattr(self, '_baseline_objects', set(bpy.data.objects.keys()))
        snaps = {}
        if getattr(context, "mode", None) == 'EDIT_MESH':
            for obj in getattr(context, "objects_in_mode", []) or []:
                if getattr(obj, "type", None) != 'MESH' or obj.data is None:
                    continue
                try:
                    bm = bmesh.from_edit_mesh(obj.data)
                    me = bpy.data.meshes.new(name=f".gh_snap_{obj.name}")
                    bm.to_mesh(me)
                    snaps[obj.name] = me.name
                except Exception as e:
                    debug_print('_capture_baseline ERROR', e, key='modal')
        operator_setattr(self, '_mesh_snaps', snaps)

    def _restore_baseline(self, context) -> None:
        """Restore meshes / remove objects created since baseline. No ed.undo."""
        baseline = operator_getattr(self, '_baseline_objects', set()) or set()
        for name in list(bpy.data.objects.keys()):
            if name in baseline:
                continue
            obj = bpy.data.objects.get(name)
            if obj is not None:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                except (ReferenceError, RuntimeError):
                    ...

        snaps = operator_getattr(self, '_mesh_snaps', {}) or {}
        if snaps and getattr(context, "mode", None) == 'EDIT_MESH':
            for obj_name, mesh_name in snaps.items():
                obj = bpy.data.objects.get(obj_name)
                snap = bpy.data.meshes.get(mesh_name)
                if obj is None or snap is None or getattr(obj, "type", None) != 'MESH':
                    continue
                try:
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.clear()
                    bm.from_mesh(snap)
                    bmesh.update_edit_mesh(obj.data)
                except Exception as e:
                    debug_print('_restore_baseline ERROR', e, key='modal')

    def _free_snapshots(self) -> None:
        snaps = operator_getattr(self, '_mesh_snaps', {}) or {}
        for mesh_name in list(snaps.values()):
            me = bpy.data.meshes.get(mesh_name)
            if me is not None:
                try:
                    bpy.data.meshes.remove(me)
                except (ReferenceError, RuntimeError):
                    ...
        operator_setattr(self, '_mesh_snaps', {})

    def _run_target_operator(self):
        """EXEC target once. undo=False — we manage preview via snapshots."""
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

    def _update_preview(self) -> None:
        """Restore baseline, then re-exec with current props (no ed.undo)."""
        self._restore_baseline(bpy.context)
        err = self._run_target_operator()
        operator_setattr(self, '_applied', err is None)

    def _replace_operator_result(self, _operator_properties) -> None:
        self._update_preview()

    def _undo_on_cancel(self) -> None:
        """Cancel: restore snapshot / drop new objects. No ed.undo."""
        if operator_getattr(self, '_applied', False):
            self._restore_baseline(bpy.context)
        operator_setattr(self, '_applied', False)
        self._free_snapshots()

    def modal(self, context, event):
        self.init_modal(event)
        pref = get_pref()
        fps = max(1, pref.gesture_property.modal_operator_target_fps)
        frame_time = 1.0 / fps
        if self.last_running_time > frame_time:
            from bpy.app.translations import pgettext
            self.report(
                {'ERROR'},
                pgettext("Operator execution took too long (%.3f s)") % self.last_running_time,
            )
            self._undo_on_cancel()
            return self.exit(context, event)
        if event.type == "LEFTMOUSE" and event.value == "PRESS":  # Confirm
            self.finished(context)
            return self.exit(context, event)

        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if event.value == "PRESS" and (self.is_right_mouse or event.type == "ESC"):
            debug_print("esc undo", key='modal')
            self._undo_on_cancel()
            return self.exit(context, event)
        if event.type not in ("TIMER_REPORT",):
            element = self.element
            if element.run_element_modal_event(self, context, event):
                debug_print("snapshot update", key='modal')
                start_time = time.time()
                self._replace_operator_result(self.operator_properties)
                self.last_running_time = time.time() - start_time
                debug_print("last_running_time", self.last_running_time, key='modal')
                self.update_header_text(context)
                return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def update_header_text(self, context):
        context.area.header_text_set(self.element.get_header_text(self._props_dict()))

    def exit(self, context, event):
        context.area.header_text_set(None)
        self.restore_hud(context)
        self.unregister_draw()
        super().exit()
        return {"FINISHED"}

    def finished(self, context):
        """On finish, save changed properties for next operator invoke."""
        self.element.last_modal_operator_property = json.dumps(self._props_dict())
        operator_setattr(self, '_applied', False)
        self._free_snapshots()
