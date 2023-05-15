from ..utils.public import register_module_factory
from . import crud, system_ops

modules_tuple = (
    crud,
    system_ops
)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
