"""Window-set focus detection for gesture sync operator handoff.

Owns snapshot / begin / end only — no keymap or UI-menu filters.
"""

from __future__ import annotations

import bpy

from ..gesture_session import UiHandoff

# Explicit idnames that open a new OS window and must stay sync (not deferred).
SYNC_WINDOW_OPEN_IDNAMES = frozenset({
    'screen.userpref_show',
    'preferences.addon_show',
})

_SNAPSHOT_ATTR = '_window_focus_before'


def snapshot_windows() -> frozenset[int]:
    """Return ``as_pointer()`` set for current ``wm.windows``."""
    wm = getattr(bpy.context, 'window_manager', None)
    if wm is None:
        return frozenset()
    pointers: set[int] = set()
    for window in wm.windows:
        try:
            pointers.add(window.as_pointer())
        except ReferenceError:
            continue
    return frozenset(pointers)


def windows_changed(before: frozenset[int] | None, after: frozenset[int] | None) -> bool:
    """Return True when the window pointer sets differ."""
    if before is None or after is None:
        return False
    return before != after


def begin_sync_op(session) -> None:
    """Snapshot windows and set ``UiHandoff.BUSY`` (ignore WINDOW_DEACTIVATE)."""
    setattr(session, _SNAPSHOT_ATTR, snapshot_windows())
    session.set_handoff(UiHandoff.BUSY)


def end_sync_op(session) -> bool:
    """Compare windows after a sync op.

    If the set changed → ``FOCUS_CHANGED`` and return True.
    Otherwise clear handoff and return False.
    """
    before = getattr(session, _SNAPSHOT_ATTR, None)
    try:
        delattr(session, _SNAPSHOT_ATTR)
    except AttributeError:
        ...
    after = snapshot_windows()
    if windows_changed(before, after):
        session.set_handoff(UiHandoff.FOCUS_CHANGED)
        return True
    session.clear_handoff()
    return False


def is_sync_window_open_idname(idname: str) -> bool:
    """Return True for explicit sync window-open operators."""
    return bool(idname) and idname in SYNC_WINDOW_OPEN_IDNAMES
