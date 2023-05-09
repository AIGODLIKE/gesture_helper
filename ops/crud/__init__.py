from ...utils.public import register_module_factory
from . import systems_crud, ui_element_crud

modules_tuple = (
    systems_crud,
    ui_element_crud,

)

register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()


def unregister():
    unregister_mod()
