"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

from typing import Callable, Optional

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}

_MSG_GESTURE = "Gesture is running (UI updates paused)"
_MSG_ANIMATION = "Animation is playing (UI updates paused)"


def is_gesture_modal_active() -> bool:
    """True while a gesture GPU overlay modal is running."""
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        return bool(GestureGpuDraw.__active_draw_instances__)
    except Exception:
        return False


def _is_animation_busy(context) -> bool:
    screen = getattr(context, "screen", None)
    if screen is None:
        return False
    if getattr(screen, "is_animation_playing", False):
        return True
    return bool(getattr(screen, "is_scrubbing", False))


def heavy_panel_skip_message(context) -> Optional[str]:
    """Message when Element/Modal panels should skip heavy draw; else None.

    Covers gesture modal and animation play/scrub only. View navigation is not
    skipped: the UI region is not part of the view-modal redraw cycle, so a skip
    label would stick (and forcing UI redraws would hurt viewport FPS).
    """
    try:
        if is_gesture_modal_active():
            return _MSG_GESTURE
        if _is_animation_busy(context):
            return _MSG_ANIMATION
    except Exception:
        return None
    return None


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
