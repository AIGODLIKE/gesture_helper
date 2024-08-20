from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.icons import Icons
from ..utils.public import get_pref


class SetDirection(Operator):
    bl_idname = 'gesture.set_direction'
    bl_label = 'Set direction'

    direction: StringProperty()

    @classmethod
    def poll(cls, _):
        pref = get_pref()
        return pref.active_element

    def execute(self, _):
        get_pref().active_element.direction = self.direction
        return {'FINISHED'}

    @classmethod
    def draw_direction(cls, layout):
        column = layout.column(align=True)
        column.emboss = 'NONE'
        row = column.row(align=True)
        for index, v in enumerate(('4', '3', '2', '5', None, '1', '6', '7', '8')):
            direction = str(v)
            is_row = index % 3 == 0
            if is_row:
                row = column.row(align=True)
            if v:
                row.operator(cls.bl_idname, text='', icon_value=Icons.get(direction).icon_id).direction = direction
            else:
                ae = get_pref().active_element
                row.label(icon_value=Icons.get(ae.direction).icon_id)
