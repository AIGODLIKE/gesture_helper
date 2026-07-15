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
    # Must register at add-on startup (not lazily on first gesture use).
    # WM GestureStore is SKIP_SAVE: File > Open / Load Factory Settings wipes it.
    # Without a persistent load_post handler, gestures would stay empty after every
    # file load until the user manually re-triggers init.
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
    try:
        # WM GestureStore is SKIP_SAVE: File > Open often resets it to empty.
        # Reload from CONFIG only when the session store was wiped.
        from .utils.gesture_persistence import (
            load_gestures_from_disk,
            suppress_gesture_disk_save,
        )
        from .utils.gesture_store import get_gestures
        from .utils.selection import suppress_radio_updates
        with suppress_radio_updates(), suppress_gesture_disk_save():
            gestures = get_gestures()
            if gestures is None or len(gestures) == 0:
                load_gestures_from_disk()
            _sync_addon_state()
    except (KeyError, AttributeError, RuntimeError):
        ...
    return None


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


def register():
    from .utils.pref import clear_pref_cache
    from .utils.session_state import SessionState
    from .utils import icons
    from .utils.texture import Texture
    from .utils.public_gpu import clear_gpu_caches

    clear_pref_cache()
    SessionState.clear()
    Texture.clear()
    clear_gpu_caches()
    icons.Icons.register()

    for module in module_list:
        module.register()

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
    from .utils.ui_draw_sync import cancel_all as cancel_ui_draw_sync

    _unregister_load_post_handler()
    cancel_poll_cache_timer()
    cancel_scheduled_gesture_save()
    cancel_ui_draw_sync()
    GestureHandle.cancel_active_gesture_timeout_timer()

    global _deferred_init_done
    _deferred_init_done = False

    create_panel_menu.stop_adding()
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

    from .utils.gesture_store import get_gesture_store
    store = get_gesture_store()
    if store is not None:
        with suppress_gesture_disk_save():
            store.gesture.clear()

    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
    from .utils.texture import Texture
    from .utils.public_gpu import clear_gpu_caches
    Texture.clear()
    clear_gpu_caches()
    clear_temp_keymap()
