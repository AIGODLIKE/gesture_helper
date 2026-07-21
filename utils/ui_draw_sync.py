"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

import time
from typing import Callable, Optional

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}

_MSG_GESTURE = "Gesture is running (UI updates paused)"
_MSG_ANIMATION = "Animation is playing (UI updates paused)"

# Throttle panel-draw debug spam (one summary line per where per interval).
_panel_debug_last: dict[str, float] = {}
_PANEL_DEBUG_INTERVAL = 0.25


def is_gesture_modal_active() -> bool:
    """True while a real gesture modal is running.

    The gesture preview also registers a draw instance, but it must NOT pause
    panel drawing — editing elements while previewing is the whole point.
    """
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        from .session_state import SessionState
        count = len(GestureGpuDraw.__active_draw_instances__)
        if SessionState.gesture_preview_active:
            count -= 1
        return count > 0
    except Exception:
        return False


def _is_animation_busy(context) -> bool:
    screen = getattr(context, "screen", None)
    if screen is None:
        return False
    if getattr(screen, "is_animation_playing", False):
        return True
    return bool(getattr(screen, "is_scrubbing", False))


def _modal_operator_ids(context) -> list[str]:
    """bl_idname-like identifiers currently on the window modal stack."""
    window = getattr(context, "window", None)
    if window is None:
        return []
    out = []
    try:
        for op in window.modal_operators:
            bl = getattr(op, "bl_idname", None)
            if bl:
                out.append(bl)
            else:
                out.append(type(op).__name__)
    except Exception:
        return out
    return out


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


def panel_draw_trace(where: str, context, *, skipped: Optional[str] = None, ms: float = 0.0) -> None:
    """Log panel draw interference facts when Debug panel draw is on."""
    from .debug_util import get_debug
    if not get_debug('panel'):
        return
    now = time.perf_counter()
    last = _panel_debug_last.get(where, 0.0)
    # Always log skips; throttle full draws.
    if now - last < _PANEL_DEBUG_INTERVAL and skipped is None:
        return
    _panel_debug_last[where] = now

    from .session_state import SessionState
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        draw_n = len(GestureGpuDraw.__active_draw_instances__)
    except Exception:
        draw_n = -1
    gesture_active = is_gesture_modal_active()
    preview = SessionState.gesture_preview_active
    modals = _modal_operator_ids(context)
    region = getattr(context, "region", None)
    area = getattr(context, "area", None)
    print(
        f"[gh:panel] {where}"
        f" skipped={skipped!r}"
        f" ms={ms:.2f}"
        f" gesture_modal={gesture_active}"
        f" preview={preview}"
        f" draw_instances={draw_n}"
        f" area={getattr(area, 'type', None)}"
        f" region={getattr(region, 'type', None)}"
        f" modals={modals}",
        flush=True,
    )


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
