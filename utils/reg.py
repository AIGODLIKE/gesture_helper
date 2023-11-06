from . import preferences, public, property
from .gesture import keymap
from .. import ops, ui

module_list = (
    ui,
    ops,
    property,
    preferences,
)


def register():
    public.PublicCacheData.cache_clear()

    for module in module_list:
        module.register()
    keymap.GestureKey.key_init()


def unregister():
    keymap.GestureKey.key_remove()
    for module in module_list:
        module.unregister()
