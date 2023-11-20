from . import preferences, public_cache, property, icons
from .gesture import gesture_keymap
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


def unregister():
    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
