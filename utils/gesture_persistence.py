"""Persist gesture CollectionProperty to CONFIG JSON (SKIP_SAVE in userpref)."""

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


def _apply_gesture_data(pref, gesture_data: dict) -> None:
    from ..ops.export_import import sanitize_gesture_import_data
    from ..gesture import gesture_keymap
    from .property import __set_prop__

    restore = sanitize_gesture_import_data(gesture_data)
    with suppress_radio_updates():
        pref.gesture.clear()
        if restore:
            __set_prop__(pref, 'gesture', restore)
        if len(pref.gesture):
            pref.index_gesture = min(max(pref.index_gesture, 0), len(pref.gesture) - 1)
        else:
            pref.index_gesture = 0
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


def _try_load_path(pref, path: str) -> bool:
    log_backup(f"gestures load: <- {path}")
    data = _read_gesture_file(path)
    _apply_gesture_data(pref, data['gesture'])
    log_backup(f"gestures load: ok ({len(pref.gesture)} gesture(s))")
    return True


def load_gestures_from_disk() -> bool:
    """
    Always load gestures into preferences.

    Order:
    1. Try each fixed/rotating candidate; on parse failure continue to the next
    2. If fixed files failed, also try rotating backups (corrupt CONFIG recovery)
    3. Empty-but-valid fixed file counts as success (no rotating fallback)
    4. If no file but pref.gesture still has legacy data → migrate to disk
    5. Otherwise leave empty

    Returns True when gestures were loaded or migrated from memory.
    """
    pref = get_pref()
    failed: list[str] = []
    candidates = iter_gestures_load_candidates()

    for path in candidates:
        try:
            return _try_load_path(pref, path)
        except Exception as e:
            failed.append(path)
            log_backup(f"gestures load failed ({path}): {e}")
            from .debug_util import debug_traceback
            debug_traceback(key='export_import')

    for path in iter_gestures_load_fallback_after_failure(failed):
        try:
            return _try_load_path(pref, path)
        except Exception as e:
            log_backup(f"gestures load failed ({path}): {e}")
            from .debug_util import debug_traceback
            debug_traceback(key='export_import')

    if len(pref.gesture) > 0:
        # Legacy userpref DNA still in memory after upgrade to SKIP_SAVE.
        log_backup(
            f"gestures migrate: {len(pref.gesture)} gesture(s) from preferences -> disk"
        )
        saved = save_gestures_to_disk(description='migrated_from_userpref')
        return saved is not None

    log_backup("gestures load: no file and no in-memory gestures")
    return False
