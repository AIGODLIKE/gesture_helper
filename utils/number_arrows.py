"""Geometry and state helpers for Blender-style numeric fields.

The native number widget has three independent hit regions: decrement, value
scrub, and increment.  Keep the geometry here so GPU drawing and modal input
cannot drift apart as row padding or UI scale changes.
"""

from __future__ import annotations


NUMBER_PART_DECREMENT = 'DECREMENT'
NUMBER_PART_VALUE = 'VALUE'
NUMBER_PART_INCREMENT = 'INCREMENT'
NUMBER_EDGE_BLEND = 0.28
NUMBER_HOVER_BLEND = 0.78
NUMBER_PRESSED_BLEND = 1.0


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
