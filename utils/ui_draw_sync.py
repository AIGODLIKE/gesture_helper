"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

from typing import Callable, Optional

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}

_MSG_GESTURE = "Gesture is running (UI updates paused)"
_MSG_ANIMATION = "Animation is playing (UI updates paused)"
_MSG_OPERATOR = "Operator is running (UI updates paused)"

# Any live modal pauses heavy panels, except our gesture / preview.
_MODAL_SKIP_EXCLUDE_PREFIXES = (
    "WM_OT_gesture_operator",
    "WM_OT_gesture_preview",
)

# One-shot poller: after modal skip, refresh UI once the modal ends.
_modal_ui_refresh_fn: Optional[Callable[[], Optional[float]]] = None


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
    """bl_idname-like identifiers on any window's modal stack.

    Preferences often runs in a separate window; only checking
    ``context.window`` would miss view/transform modals on the 3D window.
    """
    out: list[str] = []
    seen: set[str] = set()

    def _collect(window) -> None:
        if window is None:
            return
        try:
            for op in window.modal_operators:
                bl = getattr(op, "bl_idname", None) or type(op).__name__
                if bl not in seen:
                    seen.add(bl)
                    out.append(bl)
        except Exception:
            ...

    wm = getattr(context, "window_manager", None)
    if wm is None:
        wm = getattr(bpy.context, "window_manager", None)
    windows = getattr(wm, "windows", None) if wm is not None else None
    if windows:
        for window in windows:
            _collect(window)
    else:
        _collect(getattr(context, "window", None) or getattr(bpy.context, "window", None))
    return out


def _is_force_show_panels() -> bool:
    try:
        from .pref import get_pref
        return bool(get_pref().draw_property.force_show_panels_during_modal)
    except Exception:
        return False


def _blocking_modal_match(modals: list[str]) -> Optional[str]:
    """First modal that should pause heavy panels (excludes our gesture/preview)."""
    for mid in modals:
        if mid.startswith(_MODAL_SKIP_EXCLUDE_PREFIXES):
            continue
        return mid
    return None


def _is_blocking_modal(context) -> bool:
    return _blocking_modal_match(_modal_operator_ids(context)) is not None


def tag_gesture_ui_regions() -> None:
    """Redraw VIEW_3D UI (and Preferences) once — not WINDOW, to avoid FPS hit."""
    window = getattr(bpy.context, "window", None)
    if window is None or window.screen is None:
        return
    for area in window.screen.areas:
        if area.type not in {'VIEW_3D', 'PREFERENCES'}:
            continue
        for region in area.regions:
            if region.type == 'UI' or (area.type == 'PREFERENCES' and region.type == 'WINDOW'):
                region.tag_redraw()


def _schedule_modal_ui_refresh() -> None:
    """After skipping for a modal, poll until it ends then redraw UI once."""
    global _modal_ui_refresh_fn
    if _modal_ui_refresh_fn is not None:
        return

    def _poll():
        global _modal_ui_refresh_fn
        try:
            if _is_force_show_panels():
                _modal_ui_refresh_fn = None
                tag_gesture_ui_regions()
                return None
            if (
                    _is_blocking_modal(bpy.context)
                    or is_gesture_modal_active()
                    or _is_animation_busy(bpy.context)
            ):
                return 0.12
        except Exception:
            ...
        _modal_ui_refresh_fn = None
        try:
            tag_gesture_ui_regions()
        except Exception:
            ...
        return None

    _modal_ui_refresh_fn = _poll
    try:
        bpy.app.timers.register(_poll, first_interval=0.12)
    except Exception:
        _modal_ui_refresh_fn = None


def draw_heavy_panel_paused(layout, message: str) -> None:
    """Paused placeholder: reason label and Force show on one row."""
    row = layout.row(align=True)
    row.label(text=message, icon='INFO')
    try:
        from .pref import get_pref
        row.prop(get_pref().draw_property, 'force_show_panels_during_modal', text='Force show')
    except Exception:
        ...


def heavy_panel_skip_message(context) -> Optional[str]:
    """Message when Element/Modal panels should skip heavy draw; else None.

    Skips during gesture modal, animation play/scrub, and any other live modal.
    ``force_show_panels_during_modal`` overrides the pause. A one-shot timer
    refreshes UI after the modal ends so the pause label does not stick.
    """
    try:
        if _is_force_show_panels():
            return None
        if is_gesture_modal_active():
            _schedule_modal_ui_refresh()
            return _MSG_GESTURE
        if _is_animation_busy(context):
            _schedule_modal_ui_refresh()
            return _MSG_ANIMATION
        if _blocking_modal_match(_modal_operator_ids(context)):
            _schedule_modal_ui_refresh()
            return _MSG_OPERATOR
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
    global _modal_ui_refresh_fn
    for fn in list(_pending.values()):
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
    _pending.clear()
    if _modal_ui_refresh_fn is not None:
        try:
            if bpy.app.timers.is_registered(_modal_ui_refresh_fn):
                bpy.app.timers.unregister(_modal_ui_refresh_fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
        _modal_ui_refresh_fn = None
