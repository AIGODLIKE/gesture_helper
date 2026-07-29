"""Small, Blender-like helpers for resolving layout alignment."""

from __future__ import annotations


LAYOUT_ALIGNMENTS = frozenset({
    'EXPAND',
    'LEFT',
    'CENTER',
    'RIGHT',
    'TEXT_LEFT',
    'TEXT_CENTER',
    'TEXT_RIGHT',
})
TEXT_LAYOUT_ALIGNMENTS = frozenset({
    'TEXT_LEFT',
    'TEXT_CENTER',
    'TEXT_RIGHT',
})
ROUND_CORNERS_ALL = (True, True, True, True)
ROUND_CORNERS_NONE = (False, False, False, False)


def separator_line_width(configured_height, ui_scale) -> float:
    """Resolve one shared thin divider stroke for gestures and menus."""
    try:
        configured_height = float(configured_height)
    except (TypeError, ValueError):
        configured_height = 2.0
    try:
        ui_scale = float(ui_scale)
    except (TypeError, ValueError):
        ui_scale = 1.0
    return max(0.75, max(1.0, configured_height) * max(0.5, ui_scale) * 0.4)


def layout_group_corner_mask(
        is_layout_container,
        inherited,
        *,
        round_corners=True,
        join_parent_group=False,
):
    """Resolve the exposed corners for a nested layout group."""
    if not bool(round_corners):
        return ROUND_CORNERS_NONE
    if bool(is_layout_container) and not bool(join_parent_group):
        return ROUND_CORNERS_ALL
    return tuple(bool(value) for value in inherited)


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


def is_text_layout_alignment(value) -> bool:
    """Return whether an alignment mode changes label placement only."""
    return normalize_layout_alignment(value) in TEXT_LAYOUT_ALIGNMENTS


def layout_distribution_alignment(value) -> str:
    """Map text-only modes to the expanded item distribution they require."""
    value = normalize_layout_alignment(value)
    return 'EXPAND' if value in TEXT_LAYOUT_ALIGNMENTS else value


def layout_text_alignment(value) -> str:
    """Return the label alignment represented by a layout mode."""
    value = normalize_layout_alignment(value)
    if value == 'TEXT_CENTER':
        return 'CENTER'
    if value == 'TEXT_RIGHT':
        return 'RIGHT'
    return 'LEFT'


def resolve_text_alignment_offset(text_width, available, alignment) -> float:
    """Return the non-negative label offset inside an available text slot."""
    text_width = max(0.0, float(text_width))
    available = max(0.0, float(available))
    free = max(0.0, available - text_width)
    if alignment not in {'LEFT', 'CENTER', 'RIGHT'}:
        alignment = layout_text_alignment(alignment)
    if alignment == 'CENTER':
        return free * 0.5
    if alignment == 'RIGHT':
        return free
    return 0.0


def resolve_layout_line(sizes, available, gap, alignment):
    """Resolve one horizontal UILayout row into ``(position, width)`` pairs.

    Blender distributes available row width in proportion to each item's
    measured width.  The same proportional rule is used when content is wider
    than the row, which keeps a layout from overflowing its assigned panel.
    """
    values = tuple(max(0.0, float(size)) for size in sizes)
    if not values:
        return ()

    alignment = layout_distribution_alignment(alignment)
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


def resolve_split_line(count, available, gap, factor):
    """Resolve Blender's ``UILayout.split`` column widths.

    A zero factor divides the usable width equally. A non-zero factor assigns
    that fraction to the first item and divides the remainder equally between
    all later items. Blender keeps ``columnspace`` between split items even
    when ``align=True``; callers therefore pass the real, non-zero split gap.
    """
    count = max(0, int(count))
    if count == 0:
        return ()
    available = max(0.0, float(available))
    gap = max(0.0, float(gap))
    try:
        factor = float(factor)
    except (TypeError, ValueError):
        factor = 0.0
    factor = min(1.0, max(0.0, factor))
    usable = max(0.0, available - gap * (count - 1))
    percentage = 1.0 / count if factor == 0.0 else factor
    first_width = usable * percentage
    if count == 1:
        widths = (first_width,)
    else:
        other_width = max(0.0, usable - first_width) / (count - 1)
        widths = (first_width, *((other_width,) * (count - 1)))

    result = []
    cursor = 0.0
    for index, width in enumerate(widths):
        result.append((cursor, width))
        cursor += width
        if index + 1 < count:
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


def aligned_surface_corner_masks(
        surface_flags,
        *,
        horizontal,
        outer=ROUND_CORNERS_ALL,
        align_separators=True,
):
    """Return masks for drawable surfaces inside one aligned panel.

    When ``align_separators`` is true, non-surface children such as separators
    do not create a new rounded group. When it is false, each separator breaks
    the aligned run so the surfaces on either side expose their own corners.
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

    if align_separators:
        groups = (surface_indexes,)
    else:
        groups = []
        group = []
        previous = None
        for index in surface_indexes:
            if previous is None or index == previous + 1:
                group.append(index)
            else:
                groups.append(tuple(group))
                group = [index]
            previous = index
        if group:
            groups.append(tuple(group))

    for group in groups:
        surface_masks = aligned_child_corner_masks(
            len(group),
            horizontal=horizontal,
            outer=outer,
        )
        for index, mask in zip(group, surface_masks):
            masks[index] = mask
    return tuple(masks)
