import bpy.ops.ed

from ..utils.public import PublicOperator
from ..utils.public import get_pref


class ElementModal(PublicOperator):
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
        self.operator_properties = getattr(self.element, "operator_properties", None)
        print(self.bl_idname, self.gesture, self.element, self.operator_properties)

        bpy.ops.ed.undo_push("EXEC_DEFAULT", message="Gesture Element Modal")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print("\t", event.type, event.value)
        self.init_modal(event)
        pref = get_pref()
        if pref.gesture_property.modal_pass_view_rotation:
            if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
                return {'PASS_THROUGH'}
        if self.is_exit:
            return self.exit(context, event)
        if event.type not in ("TIMER_REPORT",):
            for e in self.element.modal_events:
                if e.execute(self, context, event):
                    ...
        return {'RUNNING_MODAL'}

    def exit(self, context, event):
        print("exit", context, event)
        return {"FINISHED"}

    def remember(self, context):
        ...

    def restore(self, context):
        ...
