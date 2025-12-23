import json

import bpy

from ..utils.public import PublicOperator, get_pref


class State:
    show_region_hud = None

    def start_hud(self, context):
        self.show_region_hud = context.space_data.show_region_hud
        context.space_data.show_region_hud = False

    def restore_hud(self, context):
        context.space_data.show_region_hud = self.show_region_hud


class ElementModal(PublicOperator, State):
    bl_idname = 'gesture.element_modal_event'
    bl_label = 'Element Modal'

    @classmethod
    def poll(cls, context):
        gesture = getattr(context, "gesture", None)
        element = getattr(context, "element", None)
        return gesture and element and element.operator_is_modal

    def invoke(self, context, event):
        self.init_invoke(event)
        self.gesture = getattr(context, "gesture", None)
        self.element = getattr(context, "element", None)
        self.operator_properties = getattr(self.element, "properties", None)
        print(self.bl_idname, self.gesture, self.element, self.operator_properties)

        bpy.ops.ed.undo_push(message="Gesture Element Modal")

        # 进入模态时要运行一次
        self.element.__running_by_bl_idname__(json.dumps(self.operator_properties))
        self.start_hud(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.header_text_set(str(self.operator_properties))
        self.init_modal(event)
        pref = get_pref()

        if event.type == "LEFTMOUSE" and event.value == "PRESS":  # 确认
            return self.exit(context, event)

        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if self.is_right_mouse:
            return self.exit(context, event)
        if event.type not in ("TIMER_REPORT",):
            if event.type not in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
                print("\t", event.type, event.value)
            element = self.element
            for e in element.modal_events:
                if e.execute(self, context, event):
                    if bpy.ops.ed.undo.poll():
                        bpy.ops.ed.undo()
                    element.__running_by_bl_idname__(json.dumps(self.operator_properties))
                    return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

    def exit(self, context, event):
        print("exit", context, event)
        context.area.header_text_set(None)
        self.restore_hud(context)
        return {"FINISHED"}
