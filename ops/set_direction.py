from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.public import get_pref


class SetDirection(Operator):
    bl_idname = 'gesture.set_direction'
    bl_label = '设置方向'

    direction: StringProperty()

    @classmethod
    def poll(cls, context):
        pref = get_pref()
        return pref.active_element

    def execute(self, context):
        get_pref().active_element.direction = self.direction
        return {'FINISHED'}
