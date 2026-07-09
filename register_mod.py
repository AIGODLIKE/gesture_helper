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

_load_post_handler = None
_deferred_init_done = False


def _register_load_post_handler():
    global _load_post_handler
    if _load_post_handler is not None:
        return
    _load_post_handler = _on_load_post
    bpy.app.handlers.load_post.append(_load_post_handler)


def _unregister_load_post_handler():
    global _load_post_handler
    if _load_post_handler is None:
        return
    try:
        bpy.app.handlers.load_post.remove(_load_post_handler)
    except ValueError:
        ...
    _load_post_handler = None


def _sync_addon_state():
    """Refresh caches and keymap sync after file load or deferred init."""
    from .utils.public import get_pref
    from .utils.selection import clear_all_active_element_caches

    get_pref.cache_clear()
    pref = get_pref()
    public_cache.PublicCacheFunc.cache_clear()
    clear_all_active_element_caches(pref)
    pref.update_state()


def _on_load_post(_dummy):
    try:
        _sync_addon_state()
        from .utils.icons import ensure_icons_loaded
        if ensure_icons_loaded():
            def _retry_icons():
                ensure_icons_loaded()
                return None
            bpy.app.timers.register(_retry_icons, first_interval=1.0)
    except (KeyError, AttributeError, RuntimeError):
        ...
    return None


def _schedule_icon_verify():
    from .utils.icons import ensure_icons_loaded

    def _verify(_):
        ensure_icons_loaded()
        return None

    bpy.app.timers.register(_verify, first_interval=0.5)


def init_register():
    from .ops.export_import import Import
    from .utils.public import get_pref
    from .utils import icons
    from .utils.selection import suppress_radio_updates
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

    _sync_addon_state()
    _register_load_post_handler()
    _schedule_icon_verify()


def register():
    from .utils.public import get_pref
    from .utils import icons

    icons.Icons.register()

    for module in module_list:
        module.register()

    get_pref.cache_clear()
    clear_temp_keymap()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_clear_legacy()

    global _deferred_init_done
    if not _deferred_init_done:
        _deferred_init_done = True
        init_register()


def unregister():
    from .utils import icons, is_blender_close
    from .utils.public import get_pref
    from .utils.selection import clear_all_active_element_caches
    from .ops.export_import import Export

    _unregister_load_post_handler()
    global _deferred_init_done
    _deferred_init_done = False

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
