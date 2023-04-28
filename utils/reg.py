import bpy

from . import (
    update,
    gesture,
    # property,
    preferences,
)
from .. import ui

mod_tuple = (
    ui,

    update,
    gesture,
    # property,
    preferences,
)


def register():
    for mod in mod_tuple:
        mod.register()
    bpy.context.preferences.addons['gesture_helper'].preferences.active_element.ui_items_collection_group.clear()


def unregister():
    for mod in mod_tuple:
        mod.unregister()
