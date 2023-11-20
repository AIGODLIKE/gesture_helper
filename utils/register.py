from . import preferences, public_cache, property
from .gesture import gesture_keymap
from .. import ops, ui

module_list = (
    ui,
    ops,
    property,
    preferences,
)


def register():
    for module in module_list:
        module.register()
    public_cache.PublicCacheData.cache_clear()
    gesture_keymap.GestureKeymap.key_init()


def unregister():
    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
