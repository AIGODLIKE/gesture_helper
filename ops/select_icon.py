from bpy.types import Operator

from ..utils.public import get_pref


class SelectIcon(Operator):
    bl_idname = 'gesture.select_icon'
    bl_label = 'Select Icon'

    @classmethod
    def poll(cls, context):
        return get_pref().active_element is not None

    def execute(self, context):
        act = get_pref().active_element
        act.icon_is_validity
        return {'FINISHED'}
