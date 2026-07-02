import bpy

from . import ops, ui, props, preferences
from .gesture import gesture_keymap
from .src import translate
from .utils import public_cache
from .gesture.temp_keymap import clear_temp_keymap

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
    from .utils.selection import clear_all_active_element_caches, suppress_radio_updates
    from .ui.panel import register as register_panel

    get_pref.cache_clear()
    pref = get_pref()
    register_panel()
    icons.Icons.register()

    with suppress_radio_updates():
        pref.preferences_restore()

        prop = getattr(pref, 'other_property', None)
        if prop and not prop.init_addon:
            prop.init_addon = True
            if len(pref.gesture) == 0:
                Import.restore()

    public_cache.PublicCacheFunc.cache_clear()
    clear_all_active_element_caches(pref)
    pref.update_state()


def register():
    from .utils.public import get_pref

    for module in module_list:
        module.register()

    get_pref.cache_clear()
    clear_temp_keymap()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_clear_legacy()

    bpy.app.timers.register(init_register, first_interval=0.1)


def unregister():
    from .utils import icons, is_blender_close
    from .utils.public import get_pref
    from .utils.selection import clear_all_active_element_caches
    from .ops.export_import import Export

    pref = get_pref()
    clear_all_active_element_caches(pref)
    public_cache.PublicCacheFunc.cache_clear()
    pref.preferences_backups()
    Export.backups(is_blender_close())
    get_pref.cache_clear()
    gesture_keymap.GestureKeymap.key_clear_legacy()

    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
    clear_temp_keymap()
