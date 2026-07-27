"""Geometry and preference helpers for Blender-style numeric field arrows."""

from __future__ import annotations


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
    return min(row_height, max(12.0, row_height * 0.72))


def number_arrow_rects(rect, slot_width: float):
    """Return decrement/increment hit rectangles inside *rect*."""
    if rect is None:
        return None, None
    x1, y1, x2, y2 = (float(value) for value in rect)
    slot = min(max(0.0, float(slot_width)), max(0.0, (x2 - x1) * 0.5))
    if slot <= 0.0:
        return None, None
    return (x1, y1, x1 + slot, y2), (x2 - slot, y1, x2, y2)


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
