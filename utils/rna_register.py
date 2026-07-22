"""Safe RNA class registration for dual-install / partial reload scenarios."""

from __future__ import annotations

import bpy


def _operator_struct_id(bl_idname: str) -> str:
    """Return Blender's RNA identifier for an operator ``bl_idname``."""
    module, separator, name = bl_idname.partition('.')
    if not separator or not module or not name:
        return bl_idname
    return f"{module.upper()}_OT_{name}"


def _unregister_stale_operator(cls) -> None:
    """Drop an older class with the same bl_idname after a module reload."""
    bl_idname = getattr(cls, 'bl_idname', None)
    if not bl_idname:
        return
    old_cls = None
    # bl_rna_get_subclass_py expects the RNA struct identifier on supported
    # Blender versions (e.g. WM_OT_gesture_element_add), not the dotted
    # operator id. Keep the dotted lookup as a compatibility fallback.
    for identifier in (_operator_struct_id(bl_idname), bl_idname):
        try:
            old_cls = bpy.types.Operator.bl_rna_get_subclass_py(identifier)
        except (AttributeError, TypeError, RuntimeError):
            continue
        if old_cls is not None:
            break
    if old_cls is None or old_cls is cls or not getattr(old_cls, 'is_registered', False):
        return
    try:
        bpy.utils.unregister_class(old_cls)
    except (RuntimeError, TypeError):
        pass


def register_classes_safe(classes) -> None:
    """Register classes; re-register when already registered so RNA props refresh.

    Skipping already-registered classes leaves stale OperatorProperties after a
    Python reload (e.g. missing ``gesture`` on ``wm.gesture_operator``).
    """
    for cls in classes:
        if getattr(cls, 'is_registered', False):
            try:
                bpy.utils.unregister_class(cls)
            except RuntimeError:
                pass
        else:
            _unregister_stale_operator(cls)
        try:
            bpy.utils.register_class(cls)
        except RuntimeError as exc:
            if 'already registered' not in str(exc).lower():
                raise


def unregister_classes_safe(classes) -> None:
    for cls in reversed(classes):
        if not getattr(cls, 'is_registered', False):
            continue
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
