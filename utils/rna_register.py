"""Safe RNA class registration for dual-install / partial reload scenarios."""

from __future__ import annotations

import bpy


def _operator_struct_id(bl_idname: str) -> str:
    """Return Blender's RNA identifier for an operator ``bl_idname``."""
    module, separator, name = bl_idname.partition('.')
    if not separator or not module or not name:
        return bl_idname
    return f"{module.upper()}_OT_{name}"


def _registered_class_identifiers(cls) -> tuple[str, ...]:
    """Return Blender RNA identifiers that can point at an older class."""
    identifiers = []
    bl_idname = getattr(cls, 'bl_idname', None)
    try:
        is_operator = issubclass(cls, bpy.types.Operator)
    except TypeError:
        is_operator = False
    if is_operator and bl_idname:
        identifiers.append(_operator_struct_id(bl_idname))
    if bl_idname:
        identifiers.append(bl_idname)
    identifiers.append(cls.__name__)
    return tuple(dict.fromkeys(identifiers))


def _find_registered_class(cls):
    """Find the live RNA class occupying the new class's identifiers."""
    identifiers = _registered_class_identifiers(cls)
    for identifier in identifiers:
        try:
            old_cls = getattr(bpy.types, identifier, None)
        except (AttributeError, RuntimeError, TypeError):
            old_cls = None
        if old_cls is not None:
            return old_cls

    # Registered PropertyGroups are not consistently exposed as normal
    # ``bpy.types`` attributes. Ask their concrete RNA base for the Python
    # subclass, using the same path for panels, menus, preferences, and ops.
    for base_name in (
            'Operator',
            'Panel',
            'Menu',
            'UIList',
            'Header',
            'PropertyGroup',
            'AddonPreferences',
    ):
        base = getattr(bpy.types, base_name, None)
        if base is None:
            continue
        try:
            if not issubclass(cls, base):
                continue
        except TypeError:
            continue
        for identifier in identifiers:
            try:
                old_cls = base.bl_rna_get_subclass_py(identifier)
            except (AttributeError, TypeError, RuntimeError):
                continue
            if old_cls is not None:
                return old_cls
    return None


# Short add-on package name ("gesture_helper") for both install layouts:
# legacy "gesture_helper.utils" and extension "bl_ext.<repo>.gesture_helper.utils".
_ADDON_SHORT_NAME = (
    (__package__ or '').rsplit('.', 1)[0].rpartition('.')[2] or 'gesture_helper'
)


def _owns_class(old_cls) -> bool:
    """Whether *old_cls* belongs to any install of this add-on/extension.

    Generic class names such as ``Element`` or ``Gesture`` can collide with
    unrelated add-ons; unregistering their classes would silently break them.
    Dual installs (legacy + extension) still match through the short name.
    """
    module = getattr(old_cls, '__module__', '') or ''
    return _ADDON_SHORT_NAME in module.split('.')


def _unregister_stale_class(cls) -> None:
    """Drop an older RNA class with the same identifier after a reload."""
    old_cls = _find_registered_class(cls)
    if old_cls is None or old_cls is cls:
        return
    if not getattr(old_cls, 'is_registered', False):
        return
    if not _owns_class(old_cls):
        return
    bpy.utils.unregister_class(old_cls)


def register_classes_safe(classes) -> None:
    """Register classes; re-register when already registered so RNA props refresh.

    Skipping an older PropertyGroup is as unsafe as skipping an operator: its
    RNA enum can stay stale even though bundled presets were updated on disk.
    """
    for cls in classes:
        if getattr(cls, 'is_registered', False):
            bpy.utils.unregister_class(cls)
        else:
            _unregister_stale_class(cls)
        bpy.utils.register_class(cls)


def unregister_classes_safe(classes) -> None:
    for cls in reversed(classes):
        if not getattr(cls, 'is_registered', False):
            continue
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
