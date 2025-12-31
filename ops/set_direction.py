import bpy
from bpy.props import StringProperty

from ..utils.enum import ENUM_GESTURE_DIRECTION
from ..utils.icons import Icons
from ..utils.public import get_pref
from ..utils.translate import translate_lines_text


class SetDirection(bpy.types.Operator):
    bl_idname = 'gesture.set_direction'
    bl_label = 'Set direction'

    direction: StringProperty()

    @classmethod
    def description(cls, context, properties):
        for (i, t, _) in ENUM_GESTURE_DIRECTION:
            if i == properties['direction']:
                return translate_lines_text(t)
        return None

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
        active_element = get_pref().active_element
        for index, v in enumerate(('4', '3', '2', '5', None, '1', '6', '7', '8')):
            direction = str(v)
            is_row = index % 3 == 0
            if is_row:
                row = column.row(align=True)
            if v:
                row.operator(cls.bl_idname, text='', icon_value=Icons.get(direction).icon_id).direction = direction
            else:
                ae = active_element
                direction = ae.direction
                row.operator(cls.bl_idname, text='', icon_value=Icons.get(direction).icon_id).direction = direction
                # row.label(icon_value=Icons.get(ae.direction).icon_id)
        # 显示底部方向
        if active_element and active_element.is_child_gesture:
            bottom = column.row()
            bottom.separator(factor=2)
            bottom.operator(cls.bl_idname, text='', icon_value=Icons.get('9').icon_id).direction = '9'
            bottom.separator()
