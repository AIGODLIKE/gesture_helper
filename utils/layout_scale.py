"""Layout scale compatibility helpers shared by import and rendering."""

from __future__ import annotations


LAYOUT_CONTAINER_TYPES = frozenset({'ROW', 'COLUMN', 'BOX', 'SPLIT'})
LAYOUT_SCALE_DEFAULT = 1.0
LAYOUT_SCALE_MIN = 0.25
LAYOUT_SCALE_MAX = 4.0


def clamp_layout_scale(value) -> float:
    """Coerce one layout scale value to the supported runtime range."""
    try:
        scale = float(value)
    except (TypeError, ValueError):
        scale = LAYOUT_SCALE_DEFAULT
    return min(LAYOUT_SCALE_MAX, max(LAYOUT_SCALE_MIN, scale))


def layout_scale_pair(node) -> tuple[float, float]:
    """Return X/Y scales, honoring explicitly stored legacy uniform data."""
    legacy = clamp_layout_scale(getattr(node, 'layout_scale', LAYOUT_SCALE_DEFAULT))
    is_property_set = getattr(node, 'is_property_set', None)

    def axis_value(name: str) -> float:
        try:
            value = getattr(node, name)
        except (AttributeError, TypeError, ValueError):
            return legacy

        if callable(is_property_set):
            try:
                if not is_property_set(name) and (
                        is_property_set('layout_scale')
                        or legacy != LAYOUT_SCALE_DEFAULT
                ):
                    return legacy
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                pass
        return clamp_layout_scale(value)

    return axis_value('layout_scale_x'), axis_value('layout_scale_y')


def migrate_legacy_layout_scales(elements: dict) -> None:
    """Copy old uniform layout scales into missing X/Y fields recursively."""
    for element in elements.values():
        if not isinstance(element, dict):
            continue
        if (
                element.get('element_type') in LAYOUT_CONTAINER_TYPES
                and 'layout_scale' in element
        ):
            legacy = element['layout_scale']
            element.setdefault('layout_scale_x', legacy)
            element.setdefault('layout_scale_y', legacy)
        nested = element.get('element')
        if isinstance(nested, dict):
            migrate_legacy_layout_scales(nested)
