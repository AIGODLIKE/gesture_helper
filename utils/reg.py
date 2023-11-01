from . import preferences
from .. import ops

module_list = (
    ops,
    preferences,
)


def register():
    for module in module_list:
        module.register()


def unregister():
    for module in module_list:
        module.unregister()
