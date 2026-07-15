"""Mouse coordinates relative to a VIEW_3D WINDOW region.

``event.mouse_region_*`` can disagree with GPU POST_PIXEL hit boxes when the
N-panel (UI region) is open — hit tests must use the same WINDOW region the
overlay is drawn into.
"""

from __future__ import annotations


def find_window_region(area):
    if area is None:
        return None
    try:
        for region in area.regions:
            if region.type == "WINDOW":
                return region
    except (AttributeError, ReferenceError):
        ...
    return None


def mouse_in_window_region(event, area) -> tuple[float, float] | None:
    """Return mouse position in the area's WINDOW region space, or None."""
    if event is None:
        return None
    region = find_window_region(area)
    if region is None:
        try:
            return float(event.mouse_region_x), float(event.mouse_region_y)
        except (AttributeError, TypeError):
            return None
    return float(event.mouse_x - region.x), float(event.mouse_y - region.y)


def ops_window_mouse(ops) -> tuple[float, float] | None:
    """Resolve WINDOW-space mouse for a gesture operator / element.ops."""
    event = getattr(ops, "event", None)
    area = getattr(ops, "area", None)
    if area is None:
        session = getattr(ops, "session", None)
        area = getattr(session, "area", None)
    return mouse_in_window_region(event, area)
