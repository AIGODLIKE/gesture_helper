import bpy

from . import ops, ui, props, preferences
from .gesture import gesture_keymap
from .utils import public_cache, icons
from .utils.public import get_pref

module_list = (
    ui,
    ops,
    preferences,
    props,
)


def register():
    icons.Icons.register()
    for module in module_list:
        module.register()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_remove()
    gesture_keymap.GestureKeymap.key_init()

    pref = get_pref()
    pref.other_property.is_move_element = False

    bpy.app.timers.register(lambda: pref.update_state(), first_interval=3)


def unregister():
    from .ops.export_import import Export
    Export.backups()

    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
