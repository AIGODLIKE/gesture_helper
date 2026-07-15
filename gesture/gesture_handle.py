"""Gesture handle helpers — timeout cancel + thin adapters for preview/operator."""

from __future__ import annotations

from ..utils.adapter import operator_getattr, operator_setattr
from .gesture_input import (
    cancel_timeout_timer,
    ensure_trajectory_seed,
    schedule_timeout_timer,
    tag_redraw_gesture_screen,
)
from .gesture_session import GestureSession


class GestureHandle:
    """Compatibility helpers shared by gesture modal operators.

    Canonical state lives on ``self.session``; prefer ``GestureInputProcessor``
    for event handling. This mixin keeps timeout/redraw utilities and a thin
    trajectory adapter used by gesture preview.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Non-RNA attrs: use operator_setattr (4.x / 5.x compatible).
        if operator_getattr(self, 'session', None) is None:
            operator_setattr(self, 'session', GestureSession())
        if not hasattr(self, '_input_processor'):
            operator_setattr(self, '_input_processor', None)

    def _get_input_processor(self):
        proc = operator_getattr(self, '_input_processor', None)
        if proc is None:
            from .gesture_input import GestureInputProcessor
            proc = GestureInputProcessor()
            operator_setattr(self, '_input_processor', proc)
        return proc

    def _tag_redraw_gesture_screen(self):
        tag_redraw_gesture_screen(self.session)

    def tag_redraw(self):
        self._tag_redraw_gesture_screen()

    def _ensure_trajectory_seed(self):
        ensure_trajectory_seed(self.session)

    def _cancel_gesture_timeout_timer(self):
        cancel_timeout_timer(self.session)
        from .gesture_input import cancel_bottom_child_dwell_timer
        cancel_bottom_child_dwell_timer(self.session)

    @classmethod
    def cancel_active_gesture_timeout_timer(cls) -> None:
        """Cancel timeout timer on the active gesture modal (call on unregister)."""
        from .gesture_draw_gpu import GestureGpuDraw
        inst = GestureGpuDraw.__active_draw_instance__
        if inst is None:
            return
        cancel = getattr(inst, '_cancel_gesture_timeout_timer', None)
        if callable(cancel):
            cancel()

    def _schedule_gesture_timeout_timer(self):
        schedule_timeout_timer(self.session, self.pref.gesture_property.timeout, self)

    def init_trajectory(self):
        """Initialize trajectory state on the session."""
        gesture_name = getattr(self, 'gesture', '') or ''
        event = getattr(self, 'event', None)
        area = getattr(self, 'area', None)
        screen = getattr(self, 'screen', None)
        self.session.reset(event, area, screen, gesture_name)

    def trajectory_event_update(self, context, event):
        """Update trajectory from modal event (preview / legacy entry)."""
        dirty = self._get_input_processor().on_event(self.session, self, event)
        if dirty:
            self.tag_redraw()
