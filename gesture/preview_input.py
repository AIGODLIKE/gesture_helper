"""Preview-only gesture input policy."""

from __future__ import annotations

import time

import bpy

from .gesture_input import (
    GestureInputProcessor,
    _enter_child_level,
    cancel_bottom_child_dwell_timer,
    tag_redraw_gesture_screen,
)


def _child_button_hovered(element, ops) -> bool:
    from ..element.extension_hit import layout_is_current

    element.ops = ops
    if not layout_is_current(element, ops):
        return False
    return bool(element.mouse_is_in_area)


def _arm_child_dwell(session, timeout_ms: float, ops) -> None:
    """Enter a preview child only after the pointer remains over its button."""
    if session._bottom_child_dwell_timer is not None:
        return
    timeout = max(timeout_ms, 1) / 1000.0
    session._bottom_child_dwell_deadline = time.time() + timeout

    def _on_dwell(*_args):
        try:
            deadline = getattr(session, "_bottom_child_dwell_deadline", None)
            if deadline is None:
                session._bottom_child_dwell_timer = None
                return None
            remaining = deadline - time.time()
            if remaining > 0.01:
                return remaining
            session._bottom_child_dwell_timer = None
            session._bottom_child_dwell_deadline = None
            if getattr(session, "modal_report_done", False):
                return None
            snap = session.snapshot
            element = snap.direction_element
            if (
                    session.phase.shows_radial_ui
                    and element is not None
                    and element.is_child_gesture
                    and _child_button_hovered(element, ops)
            ):
                _enter_child_level(session, ops, element, snap.mouse_window)
                tag_redraw_gesture_screen(session)
        except (AttributeError, ReferenceError):
            session._bottom_child_dwell_timer = None
            session._bottom_child_dwell_deadline = None
        return None

    session._bottom_child_dwell_timer = _on_dwell
    bpy.app.timers.register(_on_dwell, first_interval=timeout)


class PreviewGestureInputProcessor(GestureInputProcessor):
    """Track preview hover/navigation without changing or executing elements."""

    def _handle_property_drag(self, session, ops, event):
        return None

    def _arm_radial_property_drag(self, session, ops, event) -> None:
        return None

    def _handle_child_navigation(
            self, session, ops, snap, mouse, in_extension_ui: bool,
    ) -> None:
        element = snap.direction_element
        if (
                session.phase.shows_radial_ui
                and element is not None
                and element.is_child_gesture
                and not in_extension_ui
                and _child_button_hovered(element, ops)
        ):
            _arm_child_dwell(session, ops.pref.gesture_property.timeout, ops)
        else:
            cancel_bottom_child_dwell_timer(session)
