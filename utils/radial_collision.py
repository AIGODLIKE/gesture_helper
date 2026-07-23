"""Pure geometry helpers for radial overlay collision avoidance.

Automatic offsets are transient render state. They must never be written to
``Element.overlay_offset`` because that property is the user's persisted manual
adjustment.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable


Rect = tuple[float, float, float, float]
Vector2 = tuple[float, float]
RadialRecord = tuple[Hashable, Rect, Vector2]

_EPSILON = 1.0e-6


def translate_rect(rect: Rect, offset: Vector2) -> Rect:
    """Return *rect* translated by *offset*."""
    dx, dy = offset
    return rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy


def rects_overlap(a: Rect, b: Rect, padding: float = 0.0) -> bool:
    """Return whether two rectangles overlap or are closer than *padding*."""
    return not (
        a[2] + padding <= b[0]
        or b[2] + padding <= a[0]
        or a[3] + padding <= b[1]
        or b[3] + padding <= a[1]
    )


def _normalise(vector: Vector2) -> Vector2:
    x, y = float(vector[0]), float(vector[1])
    length = math.hypot(x, y)
    if length <= _EPSILON:
        return 0.0, -1.0
    return x / length, y / length


def _required_outward_shift(
        moving: Rect,
        obstacle: Rect,
        direction: Vector2,
        padding: float,
) -> float | None:
    """Minimum positive distance that separates *moving* from *obstacle*."""
    vx, vy = direction
    candidates: list[float] = []

    if vx > _EPSILON:
        candidates.append((obstacle[2] + padding - moving[0]) / vx)
    elif vx < -_EPSILON:
        candidates.append((moving[2] - obstacle[0] + padding) / -vx)

    if vy > _EPSILON:
        candidates.append((obstacle[3] + padding - moving[1]) / vy)
    elif vy < -_EPSILON:
        candidates.append((moving[3] - obstacle[1] + padding) / -vy)

    positive = [distance for distance in candidates if distance > _EPSILON]
    return min(positive) if positive else None


def _resolve_in_order(
        records: list[RadialRecord],
        offsets: dict[Hashable, Vector2],
        padding: float,
) -> None:
    """Resolve overlaps deterministically by moving later directions outward."""
    placed: list[RadialRecord] = []
    max_steps = max(8, len(records) * len(records) * 2)

    for key, base_rect, raw_direction in records:
        direction = _normalise(raw_direction)
        dx, dy = offsets.get(key, (0.0, 0.0))

        for _step in range(max_steps):
            current = translate_rect(base_rect, (dx, dy))
            required = 0.0
            for other_key, other_rect, _other_direction in placed:
                obstacle = translate_rect(other_rect, offsets[other_key])
                if not rects_overlap(current, obstacle, padding):
                    continue
                distance = _required_outward_shift(
                    current, obstacle, direction, padding,
                )
                if distance is not None:
                    required = max(required, distance)

            if required <= _EPSILON:
                break

            # Keep strict hit rectangles apart despite matrix rounding.
            required += 0.01
            dx += direction[0] * required
            dy += direction[1] * required

        offsets[key] = (dx, dy)
        placed.append((key, base_rect, direction))


def _clamp_offset_to_viewport(
        rect: Rect,
        offset: Vector2,
        viewport: Rect,
) -> Vector2:
    """Keep a translated rectangle in the viewport where its size permits."""
    dx, dy = offset
    moved = translate_rect(rect, offset)
    view_w = viewport[2] - viewport[0]
    view_h = viewport[3] - viewport[1]
    rect_w = moved[2] - moved[0]
    rect_h = moved[3] - moved[1]

    if rect_w <= view_w:
        if moved[0] < viewport[0]:
            dx += viewport[0] - moved[0]
        elif moved[2] > viewport[2]:
            dx += viewport[2] - moved[2]
    else:
        dx += (viewport[0] + viewport[2] - moved[0] - moved[2]) * 0.5

    if rect_h <= view_h:
        if moved[1] < viewport[1]:
            dy += viewport[1] - moved[1]
        elif moved[3] > viewport[3]:
            dy += viewport[3] - moved[3]
    else:
        dy += (viewport[1] + viewport[3] - moved[1] - moved[3]) * 0.5

    return dx, dy


def resolve_radial_collisions(
        records: Iterable[RadialRecord],
        *,
        viewport: Rect | None = None,
        padding: float = 0.0,
) -> dict[Hashable, Vector2]:
    """Return transient automatic offsets for radial overlay rectangles.

    Records must be in deterministic radial order. Each item is first pushed
    outward until it no longer overlaps already placed items. A viewport pass
    then keeps panels visible where possible. Clamping can reintroduce an
    overlap near an edge, so a final outward pass gives collision avoidance
    priority and permits overflow only when both constraints cannot be met.
    """
    ordered = list(records)
    offsets = {key: (0.0, 0.0) for key, _rect, _direction in ordered}
    if not ordered:
        return offsets

    padding = max(0.0, float(padding))
    _resolve_in_order(ordered, offsets, padding)

    if viewport is not None:
        for key, rect, _direction in ordered:
            offsets[key] = _clamp_offset_to_viewport(
                rect, offsets[key], viewport,
            )
        _resolve_in_order(ordered, offsets, padding)

    return offsets
