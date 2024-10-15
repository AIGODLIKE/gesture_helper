import bpy

from . import ops, ui, props, preferences
from .src import translate

module_list = (
    ui,
    ops,
    preferences,
    props,
    translate,
)


def init_register():
    from .ops.export_import import Import
    from .utils.public import get_pref
    from .gesture import gesture_keymap
    from .utils import public_cache
    from .ui.panel import register as register_panel
    from .utils import icons
    
    icons.Icons.register()

    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_remove()
    gesture_keymap.GestureKeymap.key_init()

    pref = get_pref()
    pref.update_state()
    register_panel()
    try:
        prop = pref.other_property
        if not prop.init_addon:
            prop.init_addon = True
            Import.restore()
    except Exception as e:
        import traceback
        traceback.print_stack()
        traceback.print_exc()
        print(e.args)


def register():
    from .ops.qucik_add.keymap import GestureQuickAddKeymap

    for module in module_list:
        try:
            module.register()
        except Exception as e:
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            print(e.args, "\n")

    GestureQuickAddKeymap.register()

    bpy.app.timers.register(init_register, first_interval=0.001)


def unregister():
    from .ops.export_import import Export
    from .gesture import gesture_keymap

    from .ops.qucik_add.keymap import GestureQuickAddKeymap
    from .utils import icons, is_blender_close

    if bpy.app.timers.is_registered(init_register):
        bpy.app.timers.unregister(init_register)
    GestureQuickAddKeymap.unregister()

    Export.backups(is_blender_close())

    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
