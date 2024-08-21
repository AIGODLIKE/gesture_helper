from bpy.props import BoolProperty
from bpy.types import PropertyGroup


class OtherProperty(PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name='Auto update operator property')
    init_addon: BoolProperty(name="Initialized addon", default=False)
