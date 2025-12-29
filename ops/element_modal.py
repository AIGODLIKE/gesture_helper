import json
import time

import bpy

from ..debug import DEBUG_MODAL_OPERATOR
from ..utils.public import PublicOperator, get_pref, PublicMouseModal


class State:
    show_region_hud = None

    def start_hud(self, context):
        self.show_region_hud = context.space_data.show_region_hud
        context.space_data.show_region_hud = False

    def restore_hud(self, context):
        context.space_data.show_region_hud = self.show_region_hud


class ElementModal(PublicOperator, State, PublicMouseModal):
    bl_idname = 'gesture.element_modal_event'
    bl_label = 'Element Modal'

    start_operator_properties: dict  # 用于鼠标模式的值
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
        self.start_operator_properties = getattr(self.element, "last_properties", None)
        self.operator_properties = self.start_operator_properties.copy()
        print(self.bl_idname, self.gesture, self.element, self.operator_properties)

        bpy.ops.ed.undo_push(message="Gesture Element Modal")

        # 进入模态时要运行一次
        self.element.__running_by_bl_idname__(json.dumps(self.operator_properties))
        self.start_hud(context)
        self.start_mouse(event)
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
                if DEBUG_MODAL_OPERATOR:
                    print("__running_by_bl_idname__", self.operator_properties)
                element.__running_by_bl_idname__(self.operator_properties)
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
        super().exit()
        return {"FINISHED"}

    def finished(self, context):
        """运行完成,将更改的属性保存到数据中,下次调用此操作符的时候沿用上一次的数据"""
        self.element.last_modal_operator_property = json.dumps(self.operator_properties)
