"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

from typing import Callable

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}


def is_gesture_modal_active() -> bool:
    """True while a gesture GPU overlay modal is running."""
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        return GestureGpuDraw.__modal_draw_count__ > 0
    except Exception:
        return False


def schedule(key: str, callback: Callable[[], None], *, delay: float = _SYNC_DEBOUNCE_SEC) -> None:
    """Run *callback* once after *delay*; coalesces repeats while pending."""
    if key in _pending:
        return
    # Gesture redraws the whole screen (incl. N-panel); syncing keymaps mid-modal
    # can restart bindings and make the direction arc hitch.
    if is_gesture_modal_active():
        return

    def _flush():
        _pending.pop(key, None)
        if is_gesture_modal_active():
            return None
        try:
            callback()
        except Exception:
            from .debug_util import debug_traceback
            debug_traceback(key='operator')
        return None

    _pending[key] = _flush
    try:
        bpy.app.timers.register(_flush, first_interval=delay)
    except Exception:
        _pending.pop(key, None)
        if is_gesture_modal_active():
            return
        try:
            callback()
        except Exception:
            from .debug_util import debug_traceback
            debug_traceback(key='operator')


def cancel_all() -> None:
    """Cancel pending draw-sync timers (call on unregister / gesture start)."""
    for fn in list(_pending.values()):
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
    _pending.clear()
