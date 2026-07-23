"""Persist gesture CollectionProperty to CONFIG JSON (WM session store)."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager

import bpy

from .backups import (
    iter_gestures_save_paths,
    iter_gestures_load_candidates,
    iter_gestures_load_fallback_after_failure,
    log_backup,
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


def capture_gesture_snapshot() -> dict | None:
    """Serialize the live WM store for restoration across the next file load."""
    if get_gesture_store() is None:
        return None
    return get_pref().get_gesture_data(True)


def _read_gesture_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    if not isinstance(data, dict) or 'gesture' not in data:
        raise ValueError("Invalid gesture file: missing 'gesture' data")
    gesture_data = data['gesture']
    if not isinstance(gesture_data, dict):
        raise ValueError("Invalid gesture file: 'gesture' must be an object")
    return data


def _write_gesture_file_atomic(path: str, export_data: dict) -> None:
    """Write and validate a gesture file before atomically replacing ``path``."""
    directory = os.path.dirname(path) or os.curdir
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        dir=directory,
        prefix=f'.{os.path.basename(path)}.',
        suffix='.tmp',
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, ensure_ascii=True, indent=2)
            file.flush()
            os.fsync(file.fileno())

        # Compare the exact JSON-compatible structure while the old file is
        # still untouched. This catches partial writes and serialization drift.
        written_data = _read_gesture_file(temp_path)
        expected_data = json.loads(json.dumps(export_data, ensure_ascii=True))
        if written_data != expected_data:
            raise ValueError('Gesture file verification failed before replace')

        os.replace(temp_path, path)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            ...


def _replace_gesture_store(store, restore: dict, index: int):
    """Replace the live collection and return lenient shortcut failures."""
    from ..gesture import gesture_keymap
    from ..gesture.gesture_keymap import suppress_keymap_restarts
    from .cache_state import CacheState
    from .property import __set_prop__

    with suppress_gesture_disk_save():
        with CacheState.batch(), suppress_radio_updates(), suppress_keymap_restarts():
            # A full rebuild prevents failed/removed RNA proxies from surviving
            # in the deferred per-gesture invalidation set.
            CacheState.mark_structure_dirty(None)
            store.gesture.clear()
            if restore:
                __set_prop__(store, 'gesture', restore)
            if len(store.gesture):
                store.index_gesture = min(max(index, 0), len(store.gesture) - 1)
            else:
                store.index_gesture = 0
        from ..gesture.gesture_relationship import get_gesture_index
        get_gesture_index.cache_clear()
        failures = gesture_keymap.GestureKeymap.key_restart()
    return failures


def _apply_gesture_data(store, gesture_data: dict, *, target_index=None) -> None:
    """Apply lenient startup data transactionally to the live WM store."""
    from ..ops.export_import import sanitize_gesture_import_data

    restore = sanitize_gesture_import_data(gesture_data)
    previous_data = get_pref().get_gesture_data(True)
    previous_index = store.index_gesture
    if target_index is None:
        target_index = previous_index

    try:
        failures = _replace_gesture_store(store, restore, target_index)
    except Exception as apply_error:
        try:
            rollback_failures = _replace_gesture_store(
                store,
                previous_data,
                previous_index,
            )
        except Exception as rollback_error:
            raise RuntimeError(
                f"gesture restore failed ({apply_error}); "
                f"rollback failed ({rollback_error})"
            ) from apply_error
        if rollback_failures:
            log_backup(
                "gestures restore rollback skipped invalid shortcut(s): "
                + "; ".join(str(failure) for failure in rollback_failures[:3])
            )
        raise
    if failures:
        log_backup(
            "gestures load skipped invalid shortcut(s): "
            + "; ".join(str(failure) for failure in failures[:3])
        )


def restore_gesture_snapshot(gesture_data: dict) -> bool:
    """Restore a file-load snapshot without requiring a writable user folder."""
    if not isinstance(gesture_data, dict):
        return False
    store = get_gesture_store()
    if store is None:
        return False
    try:
        _apply_gesture_data(store, gesture_data)
    except Exception as exc:
        log_backup(f"gestures memory restore failed: {exc}")
        from .debug_util import debug_traceback
        debug_traceback(key='export_import')
        return False
    log_backup(f"gestures memory restore: ok ({len(store.gesture)} gesture(s))")
    return True


def save_gestures_to_disk(*, description: str = 'gesture_config') -> str | None:
    """Write all gestures to CONFIG (or backups fallback). Return path or None."""
    from ..ops.export_import import Export

    try:
        if get_gesture_store() is None:
            log_backup("gestures save skipped: gesture store unavailable")
            return None
        pref = get_pref()
        export_data = Export._build_export_data(
            pref,
            all_gestures=True,
            description=description,
        )
        last_error = None
        for path in iter_gestures_save_paths():
            try:
                _write_gesture_file_atomic(path, export_data)
            except (OSError, TypeError, ValueError) as exc:
                last_error = exc
                log_backup(f"gestures save path failed ({path}): {exc}")
                continue
            count = len(export_data.get('gesture') or {})
            log_backup(f"gestures save: {count} gesture(s) -> {path}")
            return path
        if last_error is not None:
            raise last_error
        raise OSError("No Gesture Helper save path is available")
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
    from .property import get_property

    raw = {str(i): get_property(g) for i, g in enumerate(legacy)}
    _apply_gesture_data(
        store,
        raw,
        target_index=getattr(pref, "index_gesture", 0),
    )
    saved = save_gestures_to_disk(description='migrated_from_userpref')
    if saved is not None:
        clear_legacy_preferences_gestures()
    else:
        log_backup(
            "gestures migrate: restored to memory; disk write failed, "
            "legacy preferences retained for retry"
        )
    return True


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

    try:
        if _migrate_legacy_preferences_gestures(store):
            return True
    except Exception as e:
        log_backup(f"gestures legacy migration failed: {e}")
        from .debug_util import debug_traceback
        debug_traceback(key='export_import')

    log_backup("gestures load: no file and no in-memory gestures")
    return False
