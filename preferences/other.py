import bpy
from bpy.props import BoolProperty
from ..utils.public import get_pref


class OtherProperty(bpy.types.PropertyGroup):
    def update_auto_update_element_operator_properties(self, context):
        if ae := get_pref().active_element:
            ae.to_operator_tmp_kmi()

    auto_update_element_operator_properties: BoolProperty(
        name='Auto Update Operator Property',
        update=update_auto_update_element_operator_properties)
    init_addon: BoolProperty(name="Initialized addon", default=False)
