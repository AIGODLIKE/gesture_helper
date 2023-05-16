from .public import CacheHandler, register_module_factory
from .. import (
    gesture_ui,
    locale,
    res,
    ops,
    ui
)

from . import (
    property,

    log,
    update,

    # model
)

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
    CacheHandler.clear_cache()
    register_mod()


def unregister():
    CacheHandler.clear_cache()
    unregister_mod()
