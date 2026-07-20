"""Unified extension-panel hit tests (panel / right_band / vertical_travel).

Call sites pick flag subsets so executor, draw highlight, and rollback stay aligned.
"""

from __future__ import annotations

# Bit flags — combine with ``|`` / test with ``&``.
PANEL = 1
CHILD_ROW = 2
RIGHT_BAND = 4
VERTICAL_TRAVEL = 8
VERTICAL_BAND = 16

# Blocks radial direction confirm (matches GestureExecutor after 2525f0d).
BLOCKS_RADIAL = PANEL | RIGHT_BAND | CHILD_ROW

# Draw highlight / "in extension UI" without vertical travel dead zone.
ANY_UI = PANEL | RIGHT_BAND | CHILD_ROW

# Nested flyout travel tolerance (rollback only).
TRAVEL = VERTICAL_TRAVEL | RIGHT_BAND


def point_in_rect(mouse: tuple[float, float] | None, area) -> bool:
    if mouse is None or area is None:
        return False
    x1, y1, x2, y2 = area
    x, y = mouse
    return x1 < x < x2 and y1 < y < y2


def _mouse_for(el, ops=None) -> tuple[float, float] | None:
    """Prefer DrawFrameContext mouse; fall back to WINDOW-region resolution."""
    ops = ops or getattr(el, "ops", None)
    if ops is not None:
        session = getattr(ops, "session", None)
        draw_ctx = getattr(session, "draw_ctx", None) if session is not None else None
        if draw_ctx is not None and draw_ctx.mouse_region is not None:
            return draw_ctx.mouse_region
    from ..utils.region_mouse import ops_window_mouse
    return ops_window_mouse(ops)


def layout_is_current(el, ops) -> bool:
    """True when *el*'s hit boxes were stamped by the current session layout.

    GPU draw stamps ``_gesture_layout_token`` next to every hit box it writes;
    a session reset swaps the token, so boxes left by a previous gesture or a
    pre-draw state can never satisfy a hit test.
    """
    session = getattr(ops, "session", None) if ops is not None else None
    return session is not None and getattr(el, "_gesture_layout_token", None) is session.layout_token


def hit_test_extension(el, ops=None, *, mouse: tuple[float, float] | None = None) -> int:
    """Return hit flags for one extension panel element."""
    ops = ops or getattr(el, "ops", None)
    if not layout_is_current(el, ops):
        return 0
    if mouse is None:
        mouse = _mouse_for(el, ops)
    if mouse is None:
        return 0

    flags = 0
    panel = getattr(el, "extension_draw_area", None)
    if point_in_rect(mouse, panel):
        flags |= PANEL

    child_area = getattr(el, "extension_by_child_draw_area", None)
    if point_in_rect(mouse, child_area):
        flags |= CHILD_ROW

    if panel is not None:
        x1, y1, x2, y2 = panel
        x, y = mouse
        if x1 < x < x2:
            flags |= VERTICAL_BAND
            try:
                _w, h = el.extension_dimensions
            except (AttributeError, TypeError, ValueError):
                h = 0.0
            if h:
                if (y1 - h < y < y1) or (y2 < y < y2 + h):
                    flags |= VERTICAL_TRAVEL

    if _hit_right_band(el, ops, mouse):
        flags |= RIGHT_BAND

    return flags


def _hit_right_band(el, ops, mouse: tuple[float, float]) -> bool:
    extension_hover = getattr(ops, "extension_hover", None) if ops is not None else None
    if not extension_hover:
        return False
    try:
        idx = extension_hover.index(el)
    except ValueError:
        return False

    x, y = mouse

    if idx + 1 < len(extension_hover):
        nxt = extension_hover[idx + 1]
        child_area = getattr(nxt, "extension_draw_area", None)
        if point_in_rect(mouse, child_area):
            return True

    if extension_hover[-1] != el or len(extension_hover) <= 1:
        return False
    item = getattr(el, "extension_draw_area", None)
    if item is None:
        return False
    try:
        w, h = el.extension_dimensions
    except (AttributeError, TypeError, ValueError):
        return False
    x1, y1, x2, y2 = item
    return (x2 < x < x2 + w) and (y1 - h < y < y2 + h)


def hit_test_child_row(item, ops=None, *, mouse: tuple[float, float] | None = None) -> bool:
    """True when mouse is over an extension child row hit box."""
    ops = ops or getattr(item, "ops", None)
    if not layout_is_current(item, ops):
        return False
    if mouse is None:
        mouse = _mouse_for(item, ops)
    return point_in_rect(mouse, getattr(item, "extension_by_child_draw_area", None))


def stack_hits_flags(
        extension_hover: list,
        ops,
        *,
        mouse: tuple[float, float] | None = None,
) -> int:
    """OR of hit flags across the hover stack (panels + child rows)."""
    if not extension_hover:
        return 0
    if mouse is None:
        mouse = _mouse_for(extension_hover[0], ops)
    combined = 0
    for el in extension_hover:
        el.ops = ops
        combined |= hit_test_extension(el, ops, mouse=mouse)
        for item in getattr(el, "extension_items", []) or []:
            item.ops = ops
            if hit_test_child_row(item, ops, mouse=mouse):
                combined |= CHILD_ROW
    return combined


def stack_blocks_radial(extension_hover: list, ops) -> bool:
    """True when mouse is in panel / right band / child row (not vertical travel)."""
    return bool(stack_hits_flags(extension_hover, ops) & BLOCKS_RADIAL)


def stack_any_ui(extension_hover: list, ops, *, include_vertical_travel: bool = False) -> bool:
    """True when mouse is in extension UI; vertical travel optional."""
    mask = ANY_UI | (VERTICAL_TRAVEL if include_vertical_travel else 0)
    return bool(stack_hits_flags(extension_hover, ops) & mask)
