from ..utils.rna_register import register_classes_safe, unregister_classes_safe
from . import context_menu
from . import menu
from . import ui_list
from .panel import unregister as unregister_panel

operator_list = (
    ui_list.ElementTreePage,
    ui_list.GestureUIList,
    ui_list.ElementUIList,
    ui_list.ElementModalEventUIList,
    ui_list.ImportPresetUIList,
    menu.GESTURE_MT_add_element_menu,
    menu.GESTURE_MT_layout_preset_menu,
    menu.GESTURE_MT_main_action_menu,
)


def register():
    register_classes_safe(operator_list)
    context_menu.register()


def unregister():
    context_menu.unregister()
    unregister_classes_safe(operator_list)
    ui_list.clear_element_tree_cache(clear_pages=True)
    unregister_panel()
