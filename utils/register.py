from . import preferences, public_cache, property, icons
from .gesture import gesture_keymap
from .public import get_pref
from .. import ops, ui

module_list = (
    ui,
    ops,
    property,
    preferences,
)


def register():
    icons.Icons.init()
    for module in module_list:
        module.register()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_init()

    act = get_pref().active_gesture
    if act:
        act.to_temp_kmi()


def unregister():
    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
