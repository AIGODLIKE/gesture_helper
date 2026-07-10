"""Persist gesture CollectionProperty to CONFIG JSON (WM session store)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager

import bpy

from .backups import (
    iter_gestures_load_candidates,
    iter_gestures_load_fallback_after_failure,
    log_backup,
    resolve_gestures_save_path,
)
from .gesture_store import get_gesture_store
from .public import get_pref
from .selection import suppress_radio_updates

_suppress_disk_save = 0
_save_timer_pending = False
_save_timer_fn = None
_SAVE_DEBOUNCE_SEC = 0.35


@contextmanager
def suppress_gesture_disk_save():
    """Skip scheduled disk writes (register load, blend load sync)."""
    global _suppress_disk_save
    _suppress_disk_save += 1
    try:
        yield
    finally:
        _suppress_disk_save -= 1


def cancel_scheduled_gesture_save() -> None:
    """Cancel a pending debounced save timer."""
    global _save_timer_pending, _save_timer_fn
    if _save_timer_fn is not None:
        try:
            if bpy.app.timers.is_registered(_save_timer_fn):
                bpy.app.timers.unregister(_save_timer_fn)
        except Exception:
            ...
        _save_timer_fn = None
    _save_timer_pending = False


def _read_gesture_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    if not isinstance(data, dict) or 'gesture' not in data:
        raise ValueError("Invalid gesture file: missing 'gesture' data")
    gesture_data = data['gesture']
    if not isinstance(gesture_data, dict):
        raise ValueError("Invalid gesture file: 'gesture' must be an object")
    return data


def _apply_gesture_data(store, gesture_data: dict) -> None:
    from ..ops.export_import import sanitize_gesture_import_data
    from ..gesture import gesture_keymap
    from .property import __set_prop__

    restore = sanitize_gesture_import_data(gesture_data)
    with suppress_radio_updates():
        store.gesture.clear()
        if restore:
            __set_prop__(store, 'gesture', restore)
        if len(store.gesture):
            store.index_gesture = min(max(store.index_gesture, 0), len(store.gesture) - 1)
        else:
            store.index_gesture = 0
    from ..gesture.gesture_relationship import get_gesture_index
    get_gesture_index.cache_clear()
    gesture_keymap.GestureKeymap.key_restart()


def save_gestures_to_disk(*, description: str = 'gesture_config') -> str | None:
    """Write all gestures to CONFIG (or backups fallback). Return path or None."""
    from ..ops.export_import import Export

    pref = get_pref()
    path = resolve_gestures_save_path()
    try:
        export_data = Export._build_export_data(
            pref,
            all_gestures=True,
            description=description,
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, ensure_ascii=True, indent=2)
        count = len(export_data.get('gesture') or {})
        log_backup(f"gestures save: {count} gesture(s) -> {path}")
        return path
    except Exception as e:
        log_backup(f"gestures save failed: {e}")
        from .debug_util import debug_traceback
        debug_traceback(key='export_import')
        return None


def schedule_save_gestures_to_disk(*, description: str = 'structure_changed') -> None:
    """Debounced write after structural edits (add/remove/sort/copy, etc.)."""
    global _save_timer_pending, _save_timer_fn

    if _suppress_disk_save:
        return
    if _save_timer_pending:
        return

    _save_timer_pending = True

    def _flush():
        global _save_timer_pending, _save_timer_fn
        _save_timer_pending = False
        _save_timer_fn = None
        if _suppress_disk_save:
            return None
        save_gestures_to_disk(description=description)
        return None

    _save_timer_fn = _flush
    try:
        bpy.app.timers.register(_flush, first_interval=_SAVE_DEBOUNCE_SEC)
    except Exception as e:
        _save_timer_pending = False
        _save_timer_fn = None
        log_backup(f"gestures schedule save failed: {e}")
        save_gestures_to_disk(description=description)


def _try_load_path(store, path: str) -> bool:
    log_backup(f"gestures load: <- {path}")
    data = _read_gesture_file(path)
    _apply_gesture_data(store, data['gesture'])
    # Drop migration-only DNA so it cannot be confused with the WM store.
    clear_legacy_preferences_gestures()
    log_backup(f"gestures load: ok ({len(store.gesture)} gesture(s))")
    return True


def _migrate_legacy_preferences_gestures(store) -> bool:
    """Copy leftover AddonPreferences.gesture DNA into the WM store + JSON."""
    pref = get_pref()
    legacy = getattr(pref, "gesture", None)
    if legacy is None or len(legacy) == 0:
        return False

    log_backup(
        f"gestures migrate: {len(legacy)} gesture(s) from preferences -> WM/disk"
    )
    from ..ops.export_import import sanitize_gesture_import_data
    from .property import get_property, __set_prop__

    raw = {str(i): get_property(g) for i, g in enumerate(legacy)}
    restore = sanitize_gesture_import_data(raw)
    with suppress_radio_updates():
        store.gesture.clear()
        if restore:
            __set_prop__(store, 'gesture', restore)
        store.index_gesture = min(getattr(pref, "index_gesture", 0), max(len(store.gesture) - 1, 0))
    from ..gesture.gesture_relationship import get_gesture_index
    get_gesture_index.cache_clear()
    saved = save_gestures_to_disk(description='migrated_from_userpref')
    if saved is not None:
        clear_legacy_preferences_gestures()
    return saved is not None


def clear_legacy_preferences_gestures() -> None:
    """Clear migration-only gesture DNA still hanging on AddonPreferences."""
    pref = get_pref()
    legacy = getattr(pref, "gesture", None)
    if legacy is None:
        return
    with suppress_radio_updates():
        legacy.clear()
        if hasattr(pref, "index_gesture"):
            pref.index_gesture = 0


def purge_legacy_gestures_from_userpref() -> bool:
    """One-time rewrite of userpref.blend after clearing legacy gesture DNA."""
    pref = get_pref()
    other = getattr(pref, "other_property", None)
    if other is not None and getattr(other, "userpref_gestures_purged", False):
        # Still drop any leftover DNA loaded into memory this session.
        clear_legacy_preferences_gestures()
        return False

    clear_legacy_preferences_gestures()
    # Persist the flag in the same save_userpref write.
    if other is not None:
        other.userpref_gestures_purged = True
    try:
        bpy.ops.wm.save_userpref()
    except RuntimeError as e:
        log_backup(f"userpref purge failed: {e}")
        if other is not None:
            other.userpref_gestures_purged = False
        return False

    log_backup("userpref purge: cleared legacy gesture DNA and saved preferences")
    return True


def load_gestures_from_disk() -> bool:
    """
    Always load gestures into the WM session store.

    Order:
    1. Try each fixed/rotating candidate; on parse failure continue to the next
    2. If fixed files failed, also try rotating backups (corrupt CONFIG recovery)
    3. Empty-but-valid fixed file counts as success (no rotating fallback)
    4. If no file but AddonPreferences still has legacy data → migrate to store/disk
    5. Otherwise leave empty

    Returns True when gestures were loaded or migrated from memory.
    """
    store = get_gesture_store()
    if store is None:
        log_backup("gestures load: gesture store unavailable")
        return False

    failed: list[str] = []
    candidates = iter_gestures_load_candidates()

    for path in candidates:
        try:
            return _try_load_path(store, path)
        except Exception as e:
            failed.append(path)
            log_backup(f"gestures load failed ({path}): {e}")
            from .debug_util import debug_traceback
            debug_traceback(key='export_import')

    for path in iter_gestures_load_fallback_after_failure(failed):
        try:
            return _try_load_path(store, path)
        except Exception as e:
            log_backup(f"gestures load failed ({path}): {e}")
            from .debug_util import debug_traceback
            debug_traceback(key='export_import')

    if _migrate_legacy_preferences_gestures(store):
        return True

    log_backup("gestures load: no file and no in-memory gestures")
    return False
