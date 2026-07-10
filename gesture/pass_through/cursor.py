"""Shift+RMB 3D cursor pass-through."""

from __future__ import annotations

from ...utils.debug_util import debug_print
from .invoke import invoke_operator_now


def is_cursor_transform_kmi(kmi) -> bool:
    """True for the default Shift+RMB cursor placement binding."""
    if kmi.idname == 'view3d.cursor3d':
        return True
    if kmi.idname != 'transform.translate':
        return False
    props = kmi.properties
    if props is None:
        return False
    return bool(getattr(props, 'cursor_transform', False)) and bool(
        getattr(props, 'release_confirm', False)
    )


def try_pass_set_cursor3d_location(owner, context, event, kmi, area=None) -> bool:
    """Pass through 3D cursor placement (Shift+RMB quick click).

    Must run synchronously: ``view3d.cursor3d`` needs the current mouse event.
    """
    if not (
            event.shift
            and not event.ctrl
            and not event.alt
            and not getattr(event, 'oskey', False)
            and event.type in {'RIGHTMOUSE', 'APP'}
            and is_cursor_transform_kmi(kmi)
    ):
        return False
    if getattr(owner, 'move_count', 0) > 6:
        return False
    target_area = area or context.area
    if not target_area or target_area.type != "VIEW_3D":
        return False
    debug_print("try_pass_set_cursor3d_location", kmi.idname, key='key')
    return invoke_operator_now(context, target_area, 'view3d.cursor3d', {})
