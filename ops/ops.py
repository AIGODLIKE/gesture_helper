import bpy
from bpy.types import Operator

from ..utils.utils import PublicClass
from bpy.props import StringProperty


class RunGesture(Operator, PublicClass):
    bl_idname = 'gesture_helper.run_gesture'
    bl_label = '运行手势'

    element_name: StringProperty()

    def execute(self, context):
        print(self.bl_idname, self.element_name)
        return {'FINISHED'}


class_tuple = (
    RunGesture,
)

register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
