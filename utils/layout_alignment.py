"""Small, Blender-like helpers for resolving layout alignment."""

from __future__ import annotations


LAYOUT_ALIGNMENTS = frozenset({'EXPAND', 'LEFT', 'CENTER', 'RIGHT'})
ROUND_CORNERS_ALL = (True, True, True, True)


def blend_layout_hover_color(color, accent, amount=0.35):
    """Blend RGB toward a hover accent while preserving the source alpha."""
    source = tuple(float(value) for value in color)
    target = tuple(float(value) for value in accent)
    amount = min(1.0, max(0.0, float(amount)))
    rgb = tuple(
        source[index] + (target[index] - source[index]) * amount
        for index in range(3)
    )
    alpha = source[3] if len(source) > 3 else 1.0
    return (*rgb, alpha)


def normalize_layout_alignment(value) -> str:
    """Return a valid UILayout alignment identifier."""
    return value if value in LAYOUT_ALIGNMENTS else 'EXPAND'


def resolve_layout_line(sizes, available, gap, alignment):
    """Resolve one horizontal UILayout row into ``(position, width)`` pairs.

    Blender distributes available row width in proportion to each item's
    measured width.  The same proportional rule is used when content is wider
    than the row, which keeps a layout from overflowing its assigned panel.
    """
    values = tuple(max(0.0, float(size)) for size in sizes)
    if not values:
        return ()

    alignment = normalize_layout_alignment(alignment)
    available = max(0.0, float(available))
    gap = max(0.0, float(gap))
    item_space = max(0.0, available - gap * (len(values) - 1))
    content = sum(values)

    if content > item_space and content > 0.0:
        widths = tuple(size * item_space / content for size in values)
    elif alignment == 'EXPAND' and content > 0.0:
        widths = tuple(size * item_space / content for size in values)
    elif alignment == 'EXPAND':
        width = item_space / len(values)
        widths = (width,) * len(values)
    else:
        widths = values

    used = sum(widths) + gap * (len(values) - 1)
    free = max(0.0, available - used)
    if alignment == 'CENTER':
        cursor = free * 0.5
    elif alignment == 'RIGHT':
        cursor = free
    else:
        cursor = 0.0

    result = []
    for index, width in enumerate(widths):
        result.append((cursor, width))
        cursor += width
        if index + 1 < len(widths):
            cursor += gap
    return tuple(result)


def resolve_layout_cross_axis(size, available, alignment):
    """Resolve a child width inside a vertical layout.

    Blender's ``LayoutColumn::resolve_impl`` assigns the column width to every
    child.  ``alignment`` affects rows and button text, not the cross-axis
    geometry of a column item.
    """
    available = max(0.0, float(available))
    normalize_layout_alignment(alignment)
    return 0.0, available


def resolve_box_inset(aligned, has_children, pad_x, pad_y):
    """Return BOX content inset for the requested alignment mode.

    A populated aligned box is one continuous button group, so its child
    surfaces meet the outer border. Empty boxes retain text breathing room.
    """
    if bool(aligned) and bool(has_children):
        return 0.0, 0.0
    return max(0.0, float(pad_x)), max(0.0, float(pad_y))


def resolve_extension_row_bounds(
        content_width, row_height, margin_x, margin_y, *, fill_outer_surface=False,
):
    """Return local bounds for an ordinary bottom-extension row.

    A single action is itself the complete flyout surface, so its draw and hit
    bounds include the flyout margins. Multi-row flyouts retain an inset
    between each row and the shared outer panel.
    """
    width = max(0.0, float(content_width))
    height = max(0.0, float(row_height))
    margin_x = max(0.0, float(margin_x))
    margin_y = max(0.0, float(margin_y))
    if fill_outer_surface:
        return (
            -margin_x,
            -height - margin_y,
            width + margin_x,
            margin_y,
        )

    surface_width = max(1.0, width + margin_x * 2.0 - margin_y * 2.0)
    left = (width - surface_width) * 0.5
    return left, -height, left + surface_width, 0.0


def aligned_child_corner_masks(count, *, horizontal, outer=ROUND_CORNERS_ALL):
    """Return Blender-style outer-corner masks for one aligned child run.

    Corner order is ``(top-left, top-right, bottom-right, bottom-left)``.
    Internal corners are squared while the run inherits only the enclosing
    layout's exposed corners, matching the result of Blender's align group and
    ``widget_roundbox_set()`` for regular row/column grids.
    """
    count = max(0, int(count))
    if count == 0:
        return ()
    top_left, top_right, bottom_right, bottom_left = tuple(bool(v) for v in outer)
    if count == 1:
        return ((top_left, top_right, bottom_right, bottom_left),)

    masks = []
    last = count - 1
    for index in range(count):
        first_item = index == 0
        last_item = index == last
        if horizontal:
            masks.append((
                top_left and first_item,
                top_right and last_item,
                bottom_right and last_item,
                bottom_left and first_item,
            ))
        else:
            masks.append((
                top_left and first_item,
                top_right and first_item,
                bottom_right and last_item,
                bottom_left and last_item,
            ))
    return tuple(masks)


def aligned_surface_corner_masks(surface_flags, *, horizontal, outer=ROUND_CORNERS_ALL):
    """Return masks for drawable surfaces inside one aligned panel.

    Non-surface children such as separators do not create a new rounded group:
    only the first and last drawable surfaces inherit the panel's exposed
    corners. This keeps every boundary inside the shared panel square.
    """
    flags = tuple(bool(value) for value in surface_flags)
    count = len(flags)
    if count == 0:
        return ()
    outer = tuple(bool(value) for value in outer)
    surface_indexes = [index for index, enabled in enumerate(flags) if enabled]
    masks = [(False, False, False, False)] * count
    if not surface_indexes:
        return tuple(masks)

    surface_masks = aligned_child_corner_masks(
        len(surface_indexes),
        horizontal=horizontal,
        outer=outer,
    )
    for index, mask in zip(surface_indexes, surface_masks):
        masks[index] = mask
    return tuple(masks)
