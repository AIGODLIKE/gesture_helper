from . import (
    update,
    gesture,
    property,
    preferences,
)
from .. import ui

mod_tuple = (
    ui,
    
    update,
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
