"""Cross-version compatibility for Blender operator arguments."""

from __future__ import annotations


_GREASE_PENCIL_MODE_ALIASES = {
    "SCULPT_GPENCIL": "SCULPT_GREASE_PENCIL",
    "PAINT_GPENCIL": "PAINT_GREASE_PENCIL",
    "WEIGHT_GPENCIL": "WEIGHT_GREASE_PENCIL",
    "VERTEX_GPENCIL": "VERTEX_GREASE_PENCIL",
}


def _enum_identifiers(operator, property_name: str) -> set[str]:
    """Return the identifiers exposed by one operator enum property."""
    if operator is None:
        return set()
    try:
        prop = operator.get_rna_type().properties.get(property_name)
        if prop is None or prop.type != "ENUM":
            return set()
        return {item.identifier for item in prop.enum_items}
    except (
            AttributeError,
            KeyError,
            ReferenceError,
            RuntimeError,
            TypeError,
            ValueError,
    ):
        return set()


def resolve_operator_properties(
        bl_idname: str,
        properties: dict,
        operator=None,
) -> dict:
    """Return runtime-compatible operator properties without mutating storage.

    Legacy presets can contain ``*_GPENCIL`` identifiers. Supported Blender
    4.3+ versions expose those modes as ``*_GREASE_PENCIL``. Resolve only
    ``object.mode_set.mode`` and only when the replacement is present in the
    live operator RNA; otherwise leave the original value intact so normal
    validation reports it.
    """
    resolved = dict(properties)
    if bl_idname != "object.mode_set":
        return resolved

    mode = resolved.get("mode")
    if not isinstance(mode, str):
        return resolved

    identifiers = _enum_identifiers(operator, "mode")
    if not identifiers or mode in identifiers:
        return resolved

    alias = _GREASE_PENCIL_MODE_ALIASES.get(mode)
    if alias in identifiers:
        resolved["mode"] = alias
    return resolved
