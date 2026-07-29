"""Shared Blender pointer-event semantics."""

from __future__ import annotations


# Blender may deliver high-frequency pointer/tablet samples as an in-between
# move.  Both types carry current pointer coordinates and must advance the same
# modal interaction state; callers may still apply their own distance threshold.
POINTER_MOVE_EVENT_TYPES = frozenset({
    'MOUSEMOVE',
    'INBETWEEN_MOUSEMOVE',
})
