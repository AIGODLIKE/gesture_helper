import bpy

from . import ops, ui, props, preferences
from .gesture import gesture_keymap
from .ops.qucik_add.keymap import GestureQuickAddKeymap
from .src import translate
from .utils import public_cache

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
    from .utils import icons
    from .ui.panel import register as register_panel

    pref = get_pref()
    try:
        register_panel()
        icons.Icons.register()

        pref.update_state()
        pref.preferences_restore()

        prop = getattr(pref, 'other_property', None)
        if prop and not prop.init_addon:
            prop.init_addon = True
            Import.restore()
    except Exception as e:
        import traceback
        traceback.print_stack()
        traceback.print_exc()
        print(e.args)


def register():
    for module in module_list:
        try:
            module.register()
        except Exception as e:
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            print(e.args, "\n")
    GestureQuickAddKeymap.register()
    public_cache.PublicCacheFunc.cache_clear()

    bpy.app.timers.register(init_register, first_interval=0.001)


def unregister():
    from .utils import icons, is_blender_close
    from .utils.public import get_pref
    from .ops.export_import import Export

    public_cache.PublicCacheFunc.cache_clear()
    GestureQuickAddKeymap.unregister()
    get_pref().preferences_backups()
    Export.backups(is_blender_close())
    gesture_keymap.GestureKeymap.key_clear_legacy()

    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
