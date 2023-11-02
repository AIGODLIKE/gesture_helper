import bpy.utils

from . import ui_list

operator_list = (
    ui_list.GestureUIList,
    ui_list.ElementUIList,
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
