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

    for module in module_list:
        module.register()
    key.GestureKey.start_load_key()


def unregister():
    key.GestureKey.stop_unload_key()
    for module in module_list:
        module.unregister()
