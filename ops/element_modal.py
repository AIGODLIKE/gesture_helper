import json
import time

import blf
import bpy
import gpu

from ..debug import DEBUG_MODAL_OPERATOR
from ..utils import get_region_height, get_region_width
from ..utils.public import PublicOperator, get_pref, PublicMouseModal
from ..utils.public_gpu import PublicGpu


class State:
    show_region_hud = None

    def start_hud(self, context):
        self.show_region_hud = context.space_data.show_region_hud
        context.space_data.show_region_hud = False

    def restore_hud(self, context):
        context.space_data.show_region_hud = self.show_region_hud


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
            self.__temp_draw__ = bpy.types.SpaceView3D.draw_handler_add(self.draw_keymap_tips, (), "WINDOW",
                                                                        'POST_PIXEL')
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_exc()
            traceback.print_stack()

    def unregister_draw(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.__temp_draw__, "WINDOW")
        self.tag_redraw()


class ElementModal(PublicOperator, State, PublicMouseModal, KeymapTips):
    bl_idname = 'gesture.element_modal_event'
    bl_label = 'Element Modal'
    bl_options = {'MACRO', 'GRAB_CURSOR', 'DEPENDS_ON_CURSOR'}

    operator_properties: dict
    last_running_time = 0

    @classmethod
    def poll(cls, context):
        gesture = getattr(context, "gesture", None)
        element = getattr(context, "element", None)
        return gesture and element and element.operator_is_modal

    def invoke(self, context, event):
        self.init_invoke(event)
        self.gesture = getattr(context, "gesture", None)
        self.element = getattr(context, "element", None)
        self.operator_properties = getattr(self.element, "last_properties", None)
        print(self.bl_idname, self.gesture, self.element, self.operator_properties)

        bpy.ops.ed.undo_push(message="Gesture Element Modal")

        # 进入模态时要运行一次
        self.element.__running_by_bl_idname__(json.dumps(self.operator_properties))
        self.start_hud(context)
        self.start_mouse(event)
        self.register_draw()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.init_modal(event)
        pref = get_pref()
        if self.last_running_time > 1 / 60:  # 至少60fps才会流畅
            text = bpy.app.translations.pgettext_iface("Running operators consumes too much time")
            self.report({'ERROR'}, f"{text} {self.last_running_time}s")
            return self.exit(context, event)
        if event.type == "LEFTMOUSE" and event.value == "PRESS":  # 确认
            self.finished(context)
            return self.exit(context, event)

        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if self.is_right_mouse or event.type == "ESC":
            if bpy.ops.ed.undo.poll():
                if DEBUG_MODAL_OPERATOR:
                    print("esc undo")
                bpy.ops.ed.undo()
            return self.exit(context, event)
        if event.type not in ("TIMER_REPORT",):
            element = self.element
            if element.run_element_modal_event(self, context, event):
                if bpy.ops.ed.undo.poll():
                    if DEBUG_MODAL_OPERATOR:
                        print("undo")
                    bpy.ops.ed.undo()
                start_time = time.time()
                operator_properties = self.operator_properties
                if DEBUG_MODAL_OPERATOR:
                    print("__running_by_bl_idname__", operator_properties)
                element.__running_by_bl_idname__(operator_properties)
                self.last_running_time = time.time() - start_time
                if DEBUG_MODAL_OPERATOR:
                    print("last_running_time", self.last_running_time)
                self.update_header_text(context)
                return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}


    def update_header_text(self, context):
        context.area.header_text_set(self.element.get_header_text(self.operator_properties))

    def exit(self, context, event):
        context.area.header_text_set(None)
        x, y = self.mouse
        context.window.cursor_warp(x=int(x), y=int(y))
        self.restore_hud(context)
        self.unregister_draw()
        super().exit()
        return {"FINISHED"}

    def finished(self, context):
        """运行完成,将更改的属性保存到数据中,下次调用此操作符的时候沿用上一次的数据"""
        self.element.last_modal_operator_property = json.dumps(self.operator_properties)
