import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.public import PublicOperator


class SystemOps(Operator):
    bl_idname = PublicOperator.ops_id_name('gesture_ops')
    bl_label = '操作符'
    system: StringProperty()

    def execute(self, context):
        print(self.system)
        return {'FINISHED'}


classes_tuple = (
    SystemOps,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
