import bpy.utils
from .. import (
    gesture_ui,
    locale,
    res
)
from . import (
    log,
    preferences,
    update,

    gesture_system,  # model
)

reg_tuple = (
    log,
    preferences,
    update,

    # module
    gesture_system,
    gesture_ui,
    locale,
    res,
)


def register_module_factory(module):
    def reg():
        for mod in module:
            mod.register()

    def un_reg():
        for mod in reversed(module):
            mod.unregister()

    return reg, un_reg


register_mod, unregister_mod = register_module_factory(reg_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
