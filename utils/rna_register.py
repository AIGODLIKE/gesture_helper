"""Safe RNA class registration for dual-install / partial reload scenarios."""

from __future__ import annotations

import bpy


def register_classes_safe(classes) -> None:
    for cls in classes:
        if getattr(cls, 'is_registered', False):
            continue
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
