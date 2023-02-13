from . import (
    gesture,
    property,
    preferences,
)

mod_tuple = (
    gesture,
    property,
    preferences,
)


def register():
    for mod in mod_tuple:
        mod.register()


def unregister():
    for mod in mod_tuple:
        mod.unregister()
