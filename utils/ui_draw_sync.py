"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

from typing import Callable

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}


def schedule(key: str, callback: Callable[[], None], *, delay: float = _SYNC_DEBOUNCE_SEC) -> None:
    """Run *callback* once after *delay*; coalesces repeats while pending."""
    if key in _pending:
        return

    def _flush():
        _pending.pop(key, None)
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
        try:
            callback()
        except Exception:
            from .debug_util import debug_traceback
            debug_traceback(key='operator')


def cancel_all() -> None:
    """Cancel pending draw-sync timers (call on unregister)."""
    for fn in list(_pending.values()):
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
    _pending.clear()
