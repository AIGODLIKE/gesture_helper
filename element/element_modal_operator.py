import bpy

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)
from ..utils.public import PublicProperty


class ElementModalOperatorEventItem(bpy.types.PropertyGroup):
    event_type: bpy.props.EnumProperty(items=all_event, default="NONE")
    property: bpy.props.StringProperty()
    value_mode: bpy.props.EnumProperty(items=[
        ("SET_VALUE", "Set Value", ""),
        ("MOUSE_Y", "Mouse Y", ""),
        ("MOUSE_X", "Mouse X", ""),
    ])

    def draw_item(self, layout):
        row = layout.row(align=True)
        row.prop(self, "event_type", text="")
        row.prop(self, "property", text="")
        row.prop(self, "value_mode", text="")


class ElementModalOperatorEventCRUE:
    class ModalPoll(bpy.types.Operator, PublicProperty):
        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return ae is not None and ae.is_operator and ae.operator_is_modal

    class ADD(ModalPoll):
        bl_label = 'Add element modal item'
        bl_idname = 'gesture.element_modal_add'

        def execute(self, context):
            element = self.active_element
            new = element.modal_events.add()
            return {"FINISHED"}

    class REMOVE(ModalPoll):
        bl_label = 'Remove element modal item'
        bl_idname = 'gesture.element_modal_remove'

        def execute(self, context):
            element = getattr(context, "modal_element", None)
            return {"FINISHED"}
