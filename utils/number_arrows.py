"""Geometry and state helpers for Blender-style numeric fields.

The native number widget has three independent hit regions: decrement, value
scrub, and increment.  Keep the geometry here so GPU drawing and modal input
cannot drift apart as row padding or UI scale changes.
"""

from __future__ import annotations

import math


NUMBER_PART_DECREMENT = 'DECREMENT'
NUMBER_PART_VALUE = 'VALUE'
NUMBER_PART_INCREMENT = 'INCREMENT'
NUMBER_EDGE_DARKEN = 0.84
NUMBER_HOVER_BLEND = 0.78
NUMBER_PRESSED_BLEND = 1.0
NUMBER_FLOAT_STEP_SCALE = 0.01


def number_edge_color(color):
    """Darken a normal side-button surface while preserving its alpha."""
    values = tuple(float(value) for value in color)
    factor = NUMBER_EDGE_DARKEN
    alpha = values[3] if len(values) > 3 else 1.0
    return tuple(value * factor for value in values[:3]) + (alpha,)


def show_number_arrows(context=None) -> bool:
    """Honor Blender's global Numeric Input Arrows preference when available."""
    try:
        if context is None:
            import bpy

            context = bpy.context
        return bool(context.preferences.view.show_number_arrows)
    except (AttributeError, ImportError, ReferenceError, RuntimeError):
        return True


def number_arrow_slot_width(row_height: float) -> float:
    row_height = max(0.0, float(row_height))
    # Native number buttons occupy most of one UI unit on each edge.  Keeping
    # the slot close to the row height also gives hover a clear button shape.
    return min(row_height, max(10.0, row_height * 0.82))


def number_arrow_rects(rect, slot_width: float):
    """Return decrement/increment hit rectangles inside *rect*."""
    if rect is None:
        return None, None
    x1, y1, x2, y2 = (float(value) for value in rect)
    slot = min(max(0.0, float(slot_width)), max(0.0, (x2 - x1) * 0.5))
    if slot <= 0.0:
        return None, None
    return (x1, y1, x1 + slot, y2), (x2 - slot, y1, x2, y2)


def number_field_rects(rect, slot_width: float):
    """Return ``(decrement, value, increment)`` rectangles for a field."""
    decrement, increment = number_arrow_rects(rect, slot_width)
    if decrement is None or increment is None:
        return None, None, None
    value = (decrement[2], decrement[1], increment[0], increment[3])
    return decrement, value, increment


def number_slider_fill_rect(value_rect, fraction, *, min_width: float = 2.0):
    """Return a slider fill contained entirely by the middle value region."""
    if value_rect is None:
        return None
    try:
        fraction = float(fraction)
        min_width = max(0.0, float(min_width))
        x1, y1, x2, y2 = (float(value) for value in value_rect)
    except (TypeError, ValueError):
        return None
    width = x2 - x1
    if not math.isfinite(fraction) or fraction <= 0.0 or width <= 0.0:
        return None
    fill_width = min(width, max(min_width, width * min(1.0, fraction)))
    return x1, y1, x1 + fill_width, y2


def number_drag_value(
        start_value,
        delta_px,
        *,
        property_type: str,
        rna_step,
        hard_min=None,
        hard_max=None,
        soft_min=None,
        soft_max=None,
        precise: bool = False,
        return_applied_delta: bool = False,
):
    """Map a pointer delta like Blender's linear ``ButtonType::Num`` path.

    When requested, also return the delta at the clamped value. Blender moves
    ``dragstartx`` by the discarded overshoot so reversing away from a soft or
    hard limit reacts immediately instead of crossing a dead zone first.
    """
    def result(value, applied_delta):
        if return_applied_delta:
            return value, applied_delta
        return value

    if property_type not in {'INT', 'FLOAT'}:
        return result(start_value, delta_px)
    try:
        start = float(start_value)
        delta = float(delta_px)
        step = abs(float(rna_step))
    except (TypeError, ValueError):
        return result(start_value, delta_px)
    if not all(math.isfinite(value) for value in (start, delta, step)):
        return result(start_value, delta)

    hard_range = _ordered_finite_range(hard_min, hard_max)
    soft_range = _ordered_finite_range(soft_min, soft_max)
    interaction_range = _expanded_soft_range(start, soft_range, hard_range)
    if property_type == 'FLOAT':
        # interface_handlers.cc:numedit_but_NUM uses
        # ``fac *= 0.01f * but->step_size`` for linear float buttons.
        factor = (step if step > 0.0 else 1.0) * NUMBER_FLOAT_STEP_SCALE
        if precise:
            factor *= 0.1
    else:
        # Blender deliberately ignores RNA step for integer drags and chooses a
        # pixel scale from the effective soft range.
        interaction_span = (
            interaction_range[1] - interaction_range[0]
            if interaction_range is not None
            else math.inf
        )
        if interaction_span > 256.0:
            factor = 1.0
        elif interaction_span > 32.0:
            factor = 0.5
        else:
            factor = 1.0 / 16.0

    raw_value = start + delta * factor
    value = _clamp_interactive_value(
        raw_value, start, hard_range, soft_range,
    )
    applied_delta = delta
    if factor and value != raw_value:
        applied_delta = (value - start) / factor
    if property_type == 'INT':
        value = int(round(value))
    else:
        value = round(value, 12)
    return result(value, applied_delta)


def number_step_value(
        current_value,
        direction,
        *,
        property_type: str,
        configured_step,
        hard_min=None,
        hard_max=None,
        soft_min=None,
        soft_max=None,
        precise: bool = False,
):
    """Step a scalar value within the same soft/hard interaction bounds."""
    if property_type not in {'INT', 'FLOAT'}:
        return current_value
    try:
        current = float(current_value)
        direction = float(direction)
        step = abs(float(configured_step))
    except (TypeError, ValueError):
        return current_value
    if not all(math.isfinite(value) for value in (current, direction, step)):
        return current_value
    if direction == 0.0:
        return current_value
    direction = 1 if direction > 0.0 else -1
    if step <= 0.0:
        step = 1.0 if property_type == 'INT' else 0.01
    if property_type == 'INT':
        step = max(1.0, float(round(step)))
    elif precise:
        step *= 0.1

    value = current + direction * step
    value = _clamp_interactive_value(
        value,
        current,
        _ordered_finite_range(hard_min, hard_max),
        _ordered_finite_range(soft_min, soft_max),
    )
    if property_type == 'INT':
        return int(round(value))
    return round(value, 12)


def _clamp_interactive_value(value, start, hard_range, soft_range):
    interaction_range = _expanded_soft_range(start, soft_range, hard_range)
    lower = interaction_range[0] if interaction_range is not None else None
    upper = interaction_range[1] if interaction_range is not None else None
    if hard_range is not None:
        lower = hard_range[0] if lower is None else max(lower, hard_range[0])
        upper = hard_range[1] if upper is None else min(upper, hard_range[1])
    if lower is not None:
        value = max(value, lower)
    if upper is not None:
        value = min(value, upper)
    return value


def _expanded_soft_range(start, soft_range, hard_range):
    """Expand RNA soft bounds to contain *start* like ``button_range_set_soft``."""
    if soft_range is None:
        return hard_range
    lower, upper = soft_range
    if start + 1e-10 < lower:
        lower = (
            -_soft_range_round_up(-start, -lower)
            if start < 0.0
            else _soft_range_round_down(start, lower)
        )
        if hard_range is not None:
            lower = max(lower, hard_range[0])
    if start - 1e-10 > upper:
        upper = (
            -_soft_range_round_down(-start, -upper)
            if start < 0.0
            else _soft_range_round_up(start, upper)
        )
        if hard_range is not None:
            upper = min(upper, hard_range[1])
    return lower, upper


def _soft_range_round_up(value, maximum):
    if value == 0.0:
        new_maximum = 0.0
    else:
        try:
            new_maximum = 10.0 ** math.ceil(math.log10(value))
        except (OverflowError, ValueError):
            return value
    if new_maximum * 0.2 >= maximum and new_maximum * 0.2 >= value:
        return new_maximum * 0.2
    if new_maximum * 0.5 >= maximum and new_maximum * 0.5 >= value:
        return new_maximum * 0.5
    return new_maximum


def _soft_range_round_down(value, maximum):
    if value == 0.0:
        new_maximum = 0.0
    else:
        try:
            new_maximum = 10.0 ** math.floor(math.log10(value))
        except (OverflowError, ValueError):
            return value
    if new_maximum * 5.0 <= maximum and new_maximum * 5.0 <= value:
        return new_maximum * 5.0
    if new_maximum * 2.0 <= maximum and new_maximum * 2.0 <= value:
        return new_maximum * 2.0
    return new_maximum


def _ordered_finite_range(minimum, maximum):
    try:
        minimum = float(minimum)
        maximum = float(maximum)
    except (TypeError, ValueError):
        return None
    if (
            not math.isfinite(minimum)
            or not math.isfinite(maximum)
            or maximum <= minimum
    ):
        return None
    return minimum, maximum


def number_arrow_chevron(row_height: float, slot_width: float):
    """Return ``(half_width, half_height, line_width)`` in screen pixels."""
    height = max(0.0, float(row_height))
    slot = max(0.0, float(slot_width))
    half_height = min(height * 0.19, slot * 0.26)
    half_height = max(2.2, half_height)
    half_width = max(1.8, half_height * 0.6)
    line_width = max(1.0, min(1.6, height * 0.055))
    return half_width, half_height, line_width


def number_field_corner_masks(field_mask=None):
    """Return round-corner masks for left, value, and right field regions."""
    if field_mask is None:
        field_mask = (True, True, True, True)
    field_mask = tuple(bool(value) for value in field_mask)
    if len(field_mask) != 4:
        raise ValueError('Numeric field corner mask must contain four values')
    return (
        (field_mask[0], False, False, field_mask[3]),
        (False, False, False, False),
        (False, field_mask[1], field_mask[2], False),
    )


def number_field_part(
        point,
        decrement_rect,
        value_rect,
        increment_rect,
) -> str | None:
    """Resolve a point to one of the native three numeric-field regions."""
    if point is None:
        return None
    if _point_in_rect(point, decrement_rect):
        return NUMBER_PART_DECREMENT
    if _point_in_rect(point, increment_rect):
        return NUMBER_PART_INCREMENT
    if _point_in_rect(point, value_rect):
        return NUMBER_PART_VALUE
    return None


def number_arrow_direction(point, decrement_rect, increment_rect) -> int:
    if point is None:
        return 0
    x, y = point
    if decrement_rect is not None:
        x1, y1, x2, y2 = decrement_rect
        if x1 <= x <= x2 and y1 <= y <= y2:
            return -1
    if increment_rect is not None:
        x1, y1, x2, y2 = increment_rect
        if x1 <= x <= x2 and y1 <= y <= y2:
            return 1
    return 0


def number_part_direction(part: str | None) -> int:
    """Map a numeric-field part to the value step used by the operator."""
    if part == NUMBER_PART_DECREMENT:
        return -1
    if part == NUMBER_PART_INCREMENT:
        return 1
    return 0


def _point_in_rect(point, rect) -> bool:
    if point is None or rect is None:
        return False
    x, y = point
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2
