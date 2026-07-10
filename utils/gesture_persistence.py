"""Persist gesture CollectionProperty to CONFIG JSON (SKIP_SAVE in userpref)."""

from __future__ import annotations

import json
import os

from .backups import (
    log_backup,
    resolve_gestures_load_path,
    resolve_gestures_save_path,
)
from .public import get_pref
from .selection import suppress_radio_updates


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


def load_gestures_from_disk() -> bool:
    """
    Always load gestures into preferences.

    Order:
    1. CONFIG / backups fixed file / rotating backup
    2. If no file but pref.gesture still has legacy data → migrate to disk
    3. Otherwise leave empty

    Returns True when gestures were loaded or migrated from memory.
    """
    pref = get_pref()
    path = resolve_gestures_load_path()

    if path:
        try:
            log_backup(f"gestures load: <- {path}")
            data = _read_gesture_file(path)
            _apply_gesture_data(pref, data['gesture'])
            log_backup(f"gestures load: ok ({len(pref.gesture)} gesture(s))")
            return True
        except Exception as e:
            log_backup(f"gestures load failed: {e}")
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
