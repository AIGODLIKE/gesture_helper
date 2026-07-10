import bpy
from bpy.props import BoolProperty
from ..utils.public import get_pref


class OtherProperty(bpy.types.PropertyGroup):
    def update_auto_update_element_operator_properties(self, context):
        ae = get_pref().active_element
        if ae and ae.is_operator and ae.operator_is_operator:
            ae.to_operator_tmp_kmi()

    auto_update_element_operator_properties: BoolProperty(
        name='Auto Update Operator Property',
        description='Automatically sync operator properties from the temporary keymap preview',
        update=update_auto_update_element_operator_properties,
    )
    init_addon: BoolProperty(
        name="Initialized addon",
        description='Internal flag set after the first successful add-on initialization',
        default=False,
    )
    userpref_gestures_purged: BoolProperty(
        name="Userpref gestures purged",
        description='Internal flag: legacy gesture DNA cleared from userpref.blend',
        default=False,
    )
