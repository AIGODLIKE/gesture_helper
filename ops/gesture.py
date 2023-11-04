# 显示操作符,
# 切换
from bpy.props import StringProperty
from bpy.types import Operator


class GestureOperator(Operator):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Opeator'

    gesture: StringProperty()

    def execute(self, context):
        print(self.bl_label, self.gesture)
        return {'FINISHED'}
