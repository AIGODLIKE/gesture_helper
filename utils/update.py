import bpy

from ..preferences import GesturePreferences

init_addon = False


def timers_update():
    global init_addon
    if not init_addon:
        GesturePreferences.register_pref()
        init_addon = True
    return 1


def register():
    bpy.app.timers.register(timers_update, first_interval=1, persistent=True)


def unregister():
    bpy.app.timers.unregister(timers_update)
    GesturePreferences.unregister_pref()
