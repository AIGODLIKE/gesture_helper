import bpy.utils

from . import context_menu
from . import panel
from . import ui_list

operator_list = (
    ui_list.GestureUIList,
    ui_list.ElementUIList,
    ui_list.ImportPresetUIList,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)


def register():
    register_classes()
    context_menu.register()


def unregister():
    panel.unregister()
    context_menu.unregister()
    unregister_classes()
