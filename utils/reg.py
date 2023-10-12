from . import register_module_factory
from .. import ui, ops, preferences

modules_tuple = (
    ui, ops, preferences
)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
