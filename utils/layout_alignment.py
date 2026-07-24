"""Small, Blender-like helpers for resolving layout alignment."""

from __future__ import annotations


LAYOUT_ALIGNMENTS = frozenset({'EXPAND', 'LEFT', 'CENTER', 'RIGHT'})


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
    """Resolve a child width inside a vertical layout."""
    available = max(0.0, float(available))
    width = min(max(0.0, float(size)), available)
    alignment = normalize_layout_alignment(alignment)
    if alignment == 'EXPAND':
        return 0.0, available
    if alignment == 'CENTER':
        return (available - width) * 0.5, width
    if alignment == 'RIGHT':
        return available - width, width
    return 0.0, width
