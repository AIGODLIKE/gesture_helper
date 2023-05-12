from .public import register_module_factory
from .. import (
    gesture_ui,
    locale,
    res,
    ops,
    ui
)

from . import (
    log,
    update,

    # model
)

from .. import preferences

modules_tuple = (
    # module
    preferences,
    gesture_ui,
    locale,
    res,
    ops,
    ui,

    # .py
    log,
    update,
)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
