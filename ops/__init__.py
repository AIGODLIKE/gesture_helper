import bpy.utils

from . import switch_ui

operator_list = (
    switch_ui.SwitchGestureWindow,
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
