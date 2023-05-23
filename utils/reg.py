from . import (log, property, update)  # model
from .public import CacheHandler, register_module_factory
from .. import gesture_ui, locale, ops, res, ui
from .. import preferences

modules_tuple = (
    ops,
    property,

    # module
    preferences,
    gesture_ui,
    locale,
    res,
    ui,

    # .py
    log,
    update,
)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    CacheHandler.cache_clear()
    register_mod()


def unregister():
    CacheHandler.cache_clear()
    unregister_mod()
    # TODO backups addon data
