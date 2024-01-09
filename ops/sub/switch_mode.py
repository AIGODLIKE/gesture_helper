import bpy
from bpy.props import EnumProperty
from bpy.types import Operator


class SwitchMode(Operator):
    bl_idname = 'gesture.switch_mode'
    bl_label = 'switch mode'
    type: EnumProperty(items=[
        ('SWITCH_OBJECT_MODE', 'Toggle object mode', ''),
        ('SWITCH_OBJECT_EDIT_MODE', 'Toggle object edit mode', ''),
    ])
    select_mode: EnumProperty(items=[
        ('VERT', 'VERT', ''),
        ('EDGE', 'EDGE', ''),
        ('FACE', 'FACE', ''),
    ], options={"ENUM_FLAG"})

    def execute(self, context):
        if self.type == 'SWITCH_OBJECT_EDIT_MODE':
            bpy.ops.object.mode_set(mode='EDIT')
            for index, i in enumerate(self.select_mode):
                # {'use_extend': False, 'action': 'TOGGLE', 'use_expand': False, 'type': 'VERT'}
                if index == 0:
                    bpy.ops.mesh.select_mode(type=i, use_extend=False, action='TOGGLE', use_expand=False)
                else:
                    bpy.ops.mesh.select_mode(type=i, use_extend=True, action='ENABLE', use_expand=False)

        return {"FINISHED"}
