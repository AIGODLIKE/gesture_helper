from ..utils.public import register_module_factory
from . import template_list

modules_tuple = (
    template_list,

)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
