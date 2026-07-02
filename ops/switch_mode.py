import bpy
from bpy.props import EnumProperty


class SwitchMode(bpy.types.Operator):
    bl_idname = 'wm.gesture_switch_mode'
    bl_label = 'Switch mode'
    type: EnumProperty(items=[
        ('SWITCH_OBJECT_MODE', 'Switch object mode', ''),
        ('SWITCH_OBJECT_EDIT_MODE', 'Switch object edit mode', ''),
    ])
    select_mode: EnumProperty(items=[
        ('VERT', 'VERT', ''),
        ('EDGE', 'EDGE', ''),
        ('FACE', 'FACE', ''),
    ], options={"ENUM_FLAG"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            cls.poll_message_set("Active object required")
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            return {'CANCELLED'}
        if self.type == 'SWITCH_OBJECT_MODE':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}
        if self.type == 'SWITCH_OBJECT_EDIT_MODE':
            if obj.type != 'MESH':
                self.report({'ERROR'}, "Active object must be a mesh")
                return {'CANCELLED'}
            if context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
            if not self.select_mode:
                return {'FINISHED'}
            for index, i in enumerate(self.select_mode):
                if index == 0:
                    bpy.ops.mesh.select_mode(type=i, use_extend=False, action='TOGGLE', use_expand=False)
                else:
                    bpy.ops.mesh.select_mode(type=i, use_extend=True, action='ENABLE', use_expand=False)
        return {'FINISHED'}
