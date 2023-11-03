from . import preferences, public, property
from .gesture import key
from .. import ops, ui

module_list = (
    ui,
    ops,
    property,
    preferences,
)


def register():
    public.PublicCacheData.cache_clear()
    key.GestureKey.load_key()

    for module in module_list:
        module.register()


def unregister():
    for module in module_list:
        module.unregister()

    key.GestureKey.unload_key()
