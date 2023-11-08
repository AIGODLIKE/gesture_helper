import bpy.utils

from . import ui_list

operator_list = (
    ui_list.GestureUIList,
    ui_list.ElementUIList,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)


def register():
    register_classes()


def unregister():
    unregister_classes()
