import bpy

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)


class ModalOperatorEventItem:
    event_type: bpy.props.EnumProperty(items=all_event, default="NONE")
    property: bpy.props.StringProperty()
    value_mode: bpy.props.EnumProperty(items=[
        ("SET_VALUE", "Set Value", ""),
        ("MOUSE_Y", "Mouse Y", ""),
        ("MOUSE_X", "Mouse X", ""),
    ])
