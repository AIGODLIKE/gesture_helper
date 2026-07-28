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
    closing_target: object | None = None
    closing_target_key: tuple[str, int] | None = None
    closing_tooltip: object | None = None
    close_started_at: float = 0.0
    close_start_reveal: float = 0.0
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
    state.closing_target = None
    state.closing_target_key = None
    state.closing_tooltip = None
    state.close_started_at = 0.0
    state.close_start_reveal = 0.0


def _smoothstep(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


def _clear_closing(state: HoverTooltipState) -> None:
    state.closing_target = None
    state.closing_target_key = None
    state.closing_tooltip = None
    state.close_started_at = 0.0
    state.close_start_reveal = 0.0


def _tooltip_reveal_at(
        state: HoverTooltipState | None,
        target,
        now: float,
) -> float:
    if state is None:
        return 0.0
    key = _target_key(target)
    if state.target_key == key and key is not None:
        elapsed = now - state.show_started_at
        if elapsed <= 0.0:
            return 0.0
        return _smoothstep(elapsed / TOOLTIP_FADE_SECONDS)
    if state.closing_target_key == key and key is not None:
        elapsed = now - state.close_started_at
        if elapsed <= 0.0:
            return state.close_start_reveal
        return state.close_start_reveal * (
            1.0 - _smoothstep(elapsed / TOOLTIP_FADE_SECONDS)
        )
    return 0.0


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

    now = time.monotonic()
    current_reveal = _tooltip_reveal_at(state, state.target, now)
    if (
            state.target is not None
            and state.tooltip is not None
            and current_reveal > 0.0
    ):
        state.closing_target = state.target
        state.closing_target_key = state.target_key
        state.closing_tooltip = state.tooltip
        state.close_started_at = now
        state.close_start_reveal = current_reveal

    state.serial += 1
    serial = state.serial
    _cancel_timer(state)
    state.target = target
    state.target_key = key
    state.tooltip = None
    state.hover_started_at = now
    state.show_started_at = now + max(0.0, float(delay_ms)) / 1000.0
    if target is None and state.closing_target is None:
        return True

    def _animate(*_args):
        if state.serial != serial:
            return None
        try:
            current = time.monotonic()
            next_interval = None
            should_redraw = False

            if state.closing_target is not None:
                close_remaining = (
                    state.close_started_at + TOOLTIP_FADE_SECONDS - current
                )
                if close_remaining > 0.001:
                    should_redraw = True
                    next_interval = min(TOOLTIP_FRAME_SECONDS, close_remaining)
                else:
                    _clear_closing(state)
                    should_redraw = True

            if state.target_key == key and key is not None:
                if current < state.show_started_at:
                    wait = max(0.001, state.show_started_at - current)
                    next_interval = wait if next_interval is None else min(next_interval, wait)
                else:
                    should_redraw = True
                    fade_remaining = (
                        state.show_started_at + TOOLTIP_FADE_SECONDS - current
                    )
                    if fade_remaining > 0.001:
                        interval = min(TOOLTIP_FRAME_SECONDS, fade_remaining)
                        next_interval = (
                            interval
                            if next_interval is None
                            else min(next_interval, interval)
                        )

            if should_redraw:
                redraw()
            if next_interval is not None:
                return next_interval
        except (AttributeError, ReferenceError, RuntimeError):
            pass
        state.timer = None
        return None

    state.timer = _animate
    intervals = []
    if state.closing_target is not None:
        intervals.append(TOOLTIP_FRAME_SECONDS)
    if key is not None:
        intervals.append(max(0.001, state.show_started_at - now))
    first_interval = min(intervals) if intervals else TOOLTIP_FRAME_SECONDS
    try:
        import bpy

        bpy.app.timers.register(_animate, first_interval=first_interval)
    except (AttributeError, ImportError, RuntimeError, ValueError):
        state.timer = None
    return True


def tooltip_reveal(state: HoverTooltipState | None, target) -> float:
    """Return eased fade-in/out progress for *target* in the range 0..1."""
    return _tooltip_reveal_at(state, target, time.monotonic())


def tooltip_draw_data(
        state: HoverTooltipState | None,
) -> tuple[object | None, object | None, float]:
    """Return the strongest currently visible tooltip frame."""
    if state is None:
        return None, None, 0.0
    now = time.monotonic()
    current_reveal = _tooltip_reveal_at(state, state.target, now)
    closing_reveal = _tooltip_reveal_at(state, state.closing_target, now)
    if (
            state.tooltip is not None
            and current_reveal > 0.0
            and current_reveal >= closing_reveal
    ):
        return state.target, state.tooltip, current_reveal
    if state.closing_tooltip is not None and closing_reveal > 0.0:
        return state.closing_target, state.closing_tooltip, closing_reveal
    if state.tooltip is not None and current_reveal > 0.0:
        return state.target, state.tooltip, current_reveal
    return None, None, 0.0


def tooltip_plain_text(tooltip) -> str:
    """Return the complete displayed tooltip content in clipboard-friendly text."""
    if tooltip is None:
        return ""
    lines = [str(getattr(tooltip, "title", "") or "")]
    description = str(getattr(tooltip, "description", "") or "")
    if description:
        lines.append(description)
    for detail in getattr(tooltip, "details", ()):
        label = str(getattr(detail, "label", "") or "")
        value = str(getattr(detail, "value", "") or "")
        lines.append(f"{label}: {value}" if label else value)
    for issue in getattr(tooltip, "issues", ()):
        issue = str(issue or "")
        if issue:
            lines.append(f"! {issue}")
    return "\n".join(line for line in lines if line)


def copy_displayed_tooltip(state: HoverTooltipState | None, window_manager) -> bool:
    """Copy a currently visible hover tooltip without changing hover state."""
    _target, tooltip, reveal = tooltip_draw_data(state)
    if tooltip is None or reveal <= 0.0 or window_manager is None:
        return False
    text = tooltip_plain_text(tooltip)
    if not text:
        return False
    try:
        window_manager.clipboard = text
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return False
    return True
