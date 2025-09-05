import bpy
from bpy.props import BoolProperty


class OtherProperty(bpy.types.PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name='Auto Update Operator Property')
    init_addon: BoolProperty(name="Initialized addon", default=False)
