"""Delayed, animated hover state shared by gesture tooltip renderers."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable


TOOLTIP_FADE_SECONDS = 0.12
TOOLTIP_FRAME_SECONDS = 1.0 / 60.0


@dataclass
class HoverTooltipState:
    target: object | None = None
    target_key: tuple[str, int] | None = None
    tooltip: object | None = None
    hover_started_at: float = 0.0
    show_started_at: float = 0.0
    timer: object | None = None
    serial: int = 0


def _target_key(target) -> tuple[str, int] | None:
    if target is None:
        return None
    try:
        pointer = int(target.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pointer = 0
    if pointer:
        return "RNA", pointer
    return "PYTHON", id(target)


def _cancel_timer(state: HoverTooltipState) -> None:
    timer = state.timer
    state.timer = None
    if timer is None:
        return
    try:
        import bpy

        bpy.app.timers.unregister(timer)
    except (AttributeError, ImportError, RuntimeError, ValueError):
        pass


def cancel_hover_tooltip(state: HoverTooltipState | None) -> None:
    if state is None:
        return
    state.serial += 1
    _cancel_timer(state)
    state.target = None
    state.target_key = None
    state.tooltip = None
    state.hover_started_at = 0.0
    state.show_started_at = 0.0


def sync_hover_tooltip(
        state: HoverTooltipState,
        target,
        *,
        delay_ms: float,
        redraw: Callable[[], None],
) -> bool:
    """Track a hover target and schedule only the required animation redraws."""
    key = _target_key(target)
    if key == state.target_key:
        state.target = target
        return False

    state.serial += 1
    serial = state.serial
    _cancel_timer(state)
    state.target = target
    state.target_key = key
    state.tooltip = None
    now = time.monotonic()
    state.hover_started_at = now
    state.show_started_at = now + max(0.0, float(delay_ms)) / 1000.0
    if target is None:
        return True

    def _animate(*_args):
        if state.serial != serial or state.target_key != key:
            return None
        try:
            current = time.monotonic()
            if current < state.show_started_at:
                return max(0.001, state.show_started_at - current)
            redraw()
            fade_remaining = (
                state.show_started_at + TOOLTIP_FADE_SECONDS - current
            )
            if fade_remaining > 0.001:
                return min(TOOLTIP_FRAME_SECONDS, fade_remaining)
        except (AttributeError, ReferenceError, RuntimeError):
            pass
        state.timer = None
        return None

    state.timer = _animate
    first_interval = max(0.001, state.show_started_at - now)
    try:
        import bpy

        bpy.app.timers.register(_animate, first_interval=first_interval)
    except (AttributeError, ImportError, RuntimeError, ValueError):
        state.timer = None
    return True


def tooltip_reveal(state: HoverTooltipState | None, target) -> float:
    """Return eased fade-in progress for *target* in the range 0..1."""
    if state is None or state.target_key != _target_key(target):
        return 0.0
    elapsed = time.monotonic() - state.show_started_at
    if elapsed <= 0.0:
        return 0.0
    progress = min(1.0, elapsed / TOOLTIP_FADE_SECONDS)
    return progress * progress * (3.0 - 2.0 * progress)
