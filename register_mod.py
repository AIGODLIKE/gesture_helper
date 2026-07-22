import bpy
from bpy.app.handlers import persistent

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

_load_pre_handler = None
_load_post_handler = None
_load_gesture_snapshot = None
_deferred_init_done = False


def _matches_load_handler(candidate, callback) -> bool:
    return candidate is callback or (
        getattr(candidate, '__module__', None) == callback.__module__
        and getattr(candidate, '__name__', None) == callback.__name__
    )


def _ensure_load_handler(handler_list, callback):
    """Keep one current callback and discard copies left by module reloads."""
    current_found = False
    for candidate in tuple(handler_list):
        if candidate is callback and not current_found:
            current_found = True
            continue
        if _matches_load_handler(candidate, callback):
            try:
                handler_list.remove(candidate)
            except ValueError:
                ...
    if not current_found:
        handler_list.append(callback)
    return callback


def _remove_load_handler(handler_list, callback):
    for candidate in tuple(handler_list):
        if not _matches_load_handler(candidate, callback):
            continue
        try:
            handler_list.remove(candidate)
        except ValueError:
            ...


def _register_load_handlers():
    # WM GestureStore is SKIP_SAVE, so Blender wipes it during file loading.
    global _load_pre_handler, _load_post_handler
    _load_pre_handler = _ensure_load_handler(
        bpy.app.handlers.load_pre, _on_load_pre
    )
    _load_post_handler = _ensure_load_handler(
        bpy.app.handlers.load_post, _on_load_post
    )


def _unregister_load_handlers():
    global _load_pre_handler, _load_post_handler, _load_gesture_snapshot
    _remove_load_handler(
        bpy.app.handlers.load_pre, _load_pre_handler or _on_load_pre
    )
    _remove_load_handler(
        bpy.app.handlers.load_post, _load_post_handler or _on_load_post
    )
    _load_pre_handler = None
    _load_post_handler = None
    _load_gesture_snapshot = None


def _sync_addon_state():
    """Refresh caches and keymap sync after file load or deferred init."""
    from .utils.pref import clear_pref_cache, get_pref
    from .utils.selection import clear_all_active_element_caches

    clear_pref_cache()
    pref = get_pref()
    public_cache.PublicCacheFunc.cache_clear()
    clear_all_active_element_caches(pref)
    pref.update_state()


@persistent
def _on_load_pre(_dummy):
    """Flush pending global gesture edits before Blender clears the WM store."""
    global _load_gesture_snapshot
    _load_gesture_snapshot = None
    try:
        from .utils.gesture_persistence import (
            cancel_scheduled_gesture_save,
            capture_gesture_snapshot,
            save_gestures_to_disk,
        )
        try:
            _load_gesture_snapshot = capture_gesture_snapshot()
        except Exception:
            ...
        cancel_scheduled_gesture_save()
        save_gestures_to_disk(description='before_file_load')
    except (KeyError, AttributeError, RuntimeError):
        ...
    return None


@persistent
def _on_load_post(_dummy):
    global _load_gesture_snapshot
    snapshot = _load_gesture_snapshot
    _load_gesture_snapshot = None
    try:
        # WM GestureStore is SKIP_SAVE: File > Open often resets it to empty.
        from .utils.gesture_persistence import (
            load_gestures_from_disk,
            restore_gesture_snapshot,
            suppress_gesture_disk_save,
        )
        from .utils.gesture_store import get_gestures
        from .utils.selection import suppress_radio_updates
        with suppress_radio_updates(), suppress_gesture_disk_save():
            gestures = get_gestures()
            if gestures is None or len(gestures) == 0:
                restored = (
                    snapshot is not None
                    and restore_gesture_snapshot(snapshot)
                )
                if not restored:
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
    _register_load_handlers()


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
    from .utils.backups import log_backup
    from .ops.export_import import Export
    from .ops.quick_add import create_panel_menu
    from .element.element_poll import cancel_poll_cache_timer
    from .gesture.gesture_handle import GestureHandle
    from .gesture.gesture_draw_gpu import GestureGpuDraw
    from .gesture.pass_through import cancel_deferred_operator_timers
    from .utils.ui_draw_sync import cancel_all as cancel_ui_draw_sync

    _unregister_load_handlers()
    cancel_poll_cache_timer()
    cancel_scheduled_gesture_save()
    cancel_ui_draw_sync()
    GestureHandle.cancel_active_gesture_timeout_timer()
    cancel_deferred_operator_timers()
    GestureGpuDraw.force_unregister_draw()

    global _deferred_init_done
    _deferred_init_done = False

    create_panel_menu.stop_adding()
    SessionState.clear()

    pref = get_pref()
    clear_all_active_element_caches(pref)
    with suppress_gesture_disk_save():
        public_cache.PublicCacheFunc.cache_clear()
    def _shutdown_log(message):
        try:
            log_backup(message)
        except Exception:
            pass

    # Persistence is best-effort during unregister.  A read-only user folder
    # or Blender teardown must not abort class/keymap cleanup halfway through.
    try:
        save_gestures_to_disk()
    except Exception as exc:
        _shutdown_log(f"gestures shutdown save failed: {exc}")
    try:
        pref.preferences_backups()
    except Exception as exc:
        _shutdown_log(f"preferences shutdown backup failed: {exc}")
    try:
        Export.backups(is_blender_close())
    except Exception as exc:
        _shutdown_log(f"automatic shutdown backup failed: {exc}")
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
