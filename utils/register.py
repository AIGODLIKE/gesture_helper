import bpy

from . import public_cache, property, icons
from .public import get_pref
from .. import ops, ui
from .. import preferences
from ..gesture import gesture_keymap

module_list = (
    ui,
    ops,
    property,
    preferences,
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

    bpy.app.timers.register(lambda: pref.update_state(), first_interval=0.1)


def unregister():
    from ..ops.export_import import Export
    Export.backups()

    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
