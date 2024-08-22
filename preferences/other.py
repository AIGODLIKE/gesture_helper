from bpy.props import BoolProperty
from bpy.types import PropertyGroup


class OtherProperty(PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name='Auto Update Operator Property')
    init_addon: BoolProperty(name="Initialized addon", default=False)
