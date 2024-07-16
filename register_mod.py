import bpy

from . import ops, ui, props, preferences

module_list = (
    ui,
    ops,
    preferences,
    props,
)


def update_state():
    from .utils.public import get_pref
    pref = get_pref()
    pref.update_state()


def restore():
    from .ops.export_import import Import
    from .utils.public import get_pref
    from .gesture import gesture_keymap
    from .utils import public_cache

    pref = get_pref()
    try:
        prop = pref.other_property
        if not prop.init_addon:
            prop.init_addon = True
            Import.restore()
    except Exception as e:
        print(e.args)

    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_remove()
    gesture_keymap.GestureKeymap.key_init()


def register():
    from .utils.public import get_pref
    from .ops.gesture_quick_add import GestureQuickAddKeymap

    from .utils import icons
    icons.Icons.register()
    for module in module_list:
        try:
            module.register()
        except Exception as e:
            print(e.args, "\n")

    GestureQuickAddKeymap.register()
    pref = get_pref()
    if pref is not None:
        pref.other_property.is_move_element = False

    bpy.app.timers.register(update_state, first_interval=3)
    bpy.app.timers.register(restore, first_interval=0.001)


def unregister():
    from .ops.export_import import Export
    from .gesture import gesture_keymap

    from .ops.gesture_quick_add import GestureQuickAddKeymap
    from .utils import icons, is_blender_close

    if bpy.app.timers.is_registered(update_state):
        bpy.app.timers.unregister(update_state)
    if bpy.app.timers.is_registered(restore):
        bpy.app.timers.unregister(restore)
    GestureQuickAddKeymap.unregister()

    Export.backups(is_blender_close())

    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
