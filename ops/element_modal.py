import json

import bpy

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

        if event.type == "LEFTMOUSE" and event.value == "PRESS":  # 确认
            return self.exit(context, event)

        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if self.is_right_mouse or event.type == "ESC":
            if bpy.ops.ed.undo.poll():
                bpy.ops.ed.undo()
            return self.exit(context, event)
        if event.type not in ("TIMER_REPORT",):
            element = self.element
            if element.run_modal(self, context, event):
                if bpy.ops.ed.undo.poll():
                    bpy.ops.ed.undo()
                element.__running_by_bl_idname__(json.dumps(self.operator_properties))
                self.update_header_text(context)
                return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def update_header_text(self, context):

        context.area.header_text_set(self.element.get_header_text(self.operator_properties))

    def exit(self, context, event):
        print("exit", context, event)
        context.area.header_text_set(None)
        x, y = self.mouse
        context.window.cursor_warp(x=int(x), y=int(y))
        self.restore_hud(context)
        super().exit()
        return {"FINISHED"}

    def finished(self, context):
        """运行完成,将更改的属性保存到数据中,下次调用此操作符的时候沿用上一次的数据"""
        self.element.last_modal_operator_property = json.dumps(self.operator_properties)
