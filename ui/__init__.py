import bpy.utils

from . import context_menu
from . import menu
from . import ui_list
from .panel import unregister as unregister_panel

operator_list = (
    ui_list.GestureUIList,
    ui_list.ElementUIList,
    ui_list.ElementModalEventUIList,
    ui_list.ImportPresetUIList,
    menu.GESTURE_MT_add_element_menu
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)


def register():
    register_classes()
    context_menu.register()


def unregister():
    context_menu.unregister()
    unregister_classes()
    unregister_panel()
