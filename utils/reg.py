from . import register_module_factory, property
from .. import ui, ops, preferences
from ..public import CacheHandler

modules_tuple = (
    ui, ops, property, preferences
)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    CacheHandler.cache_clear()
    register_mod()


def unregister():
    unregister_mod()
