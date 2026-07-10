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
_icon_verify_timer = None
_icon_retry_timer = None


def _unregister_timer(timer) -> None:
    if timer is None:
        return
    try:
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    except (ValueError, RuntimeError, AttributeError):
        ...


def _cancel_icon_timers() -> None:
    global _icon_verify_timer, _icon_retry_timer
    _unregister_timer(_icon_verify_timer)
    _unregister_timer(_icon_retry_timer)
    _icon_verify_timer = None
    _icon_retry_timer = None


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
    from .utils.pref import clear_pref_cache, get_pref
    from .utils.selection import clear_all_active_element_caches

    clear_pref_cache()
    pref = get_pref()
    public_cache.PublicCacheFunc.cache_clear()
    clear_all_active_element_caches(pref)
    pref.update_state()


def _on_load_post(_dummy):
    global _icon_retry_timer
    try:
        from .utils.gesture_persistence import suppress_gesture_disk_save
        with suppress_gesture_disk_save():
            _sync_addon_state()
        from .utils.icons import ensure_icons_loaded
        if ensure_icons_loaded():
            def _retry_icons():
                global _icon_retry_timer
                _icon_retry_timer = None
                ensure_icons_loaded()
                return None
            _unregister_timer(_icon_retry_timer)
            _icon_retry_timer = _retry_icons
            bpy.app.timers.register(_retry_icons, first_interval=1.0)
    except (KeyError, AttributeError, RuntimeError):
        ...
    return None


def _schedule_icon_verify():
    global _icon_verify_timer
    from .utils.icons import ensure_icons_loaded

    def _verify():
        global _icon_verify_timer
        _icon_verify_timer = None
        ensure_icons_loaded()
        return None

    _unregister_timer(_icon_verify_timer)
    _icon_verify_timer = _verify
    bpy.app.timers.register(_verify, first_interval=0.5)


def init_register():
    from .utils.pref import clear_pref_cache, get_pref
    from .utils import icons
    from .utils.selection import suppress_radio_updates
    from .utils.gesture_persistence import (
        load_gestures_from_disk,
        suppress_gesture_disk_save,
    )
    from .ui.panel import register as register_panel

    clear_pref_cache()
    pref = get_pref()
    register_panel()
    icons.Icons.register()

    with suppress_radio_updates(), suppress_gesture_disk_save():
        pref.preferences_restore()
        prop = getattr(pref, 'other_property', None)
        if prop and not prop.init_addon:
            prop.init_addon = True
        load_gestures_from_disk()
        _sync_addon_state()

    _register_load_post_handler()
    _schedule_icon_verify()


def register():
    from .utils.pref import clear_pref_cache
    from .utils.session_state import SessionState
    from .utils import icons

    clear_pref_cache()
    SessionState.clear()
    icons.Icons.register()

    for module in module_list:
        module.register()

    clear_pref_cache()
    clear_temp_keymap()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_clear_legacy()

    global _deferred_init_done
    if not _deferred_init_done:
        _deferred_init_done = True
        init_register()


def unregister():
    from .utils import icons, is_blender_close
    from .utils.pref import clear_pref_cache, get_pref
    from .utils.session_state import SessionState
    from .utils.selection import clear_all_active_element_caches
    from .utils.gesture_persistence import (
        cancel_scheduled_gesture_save,
        save_gestures_to_disk,
        suppress_gesture_disk_save,
    )
    from .ops.export_import import Export
    from .ops.quick_add import create_panel_menu
    from .element.element_poll import cancel_poll_cache_timer
    from .gesture.gesture_handle import GestureHandle

    _unregister_load_post_handler()
    _cancel_icon_timers()
    cancel_poll_cache_timer()
    cancel_scheduled_gesture_save()
    GestureHandle.cancel_active_gesture_timeout_timer()

    global _deferred_init_done
    _deferred_init_done = False

    create_panel_menu.unregister()
    SessionState.clear()

    pref = get_pref()
    clear_all_active_element_caches(pref)
    with suppress_gesture_disk_save():
        public_cache.PublicCacheFunc.cache_clear()
    save_gestures_to_disk()
    pref.preferences_backups()
    Export.backups(is_blender_close())
    clear_pref_cache()
    gesture_keymap.GestureKeymap.key_clear_legacy()

    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
    clear_temp_keymap()
