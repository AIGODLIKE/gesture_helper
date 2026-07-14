"""Shared invoke / defer helpers for gesture pass-through (no business filters)."""

from __future__ import annotations

import bpy

from ...utils.debug_util import debug_print
from ..addon_keymap import get_kmi_operator_properties


def _screen_contains_area(screen, area) -> bool:
    """Check whether *screen* still contains *area* (Blender 5.x safe)."""
    if screen is None or area is None:
        return False
    try:
        area_ptr = area.as_pointer()
    except ReferenceError:
        return False
    for candidate in screen.areas:
        try:
            if candidate.as_pointer() == area_ptr:
                return True
        except ReferenceError:
            continue
    return False


def _find_window_for_area(area):
    """Return the window that contains *area* (works on Blender 4.x and 5.x)."""
    if area is None:
        return None
    wm = getattr(bpy.context, 'window_manager', None)
    if wm is None:
        return getattr(bpy.context, 'window', None)
    for window in wm.windows:
        if _screen_contains_area(window.screen, area):
            return window
    return None


def _area_is_valid(area) -> bool:
    if area is None:
        return False
    try:
        _ = area.type
    except ReferenceError:
        return False

    screen = getattr(area, 'screen', None)
    if screen is not None:
        return _screen_contains_area(screen, area)

    return _find_window_for_area(area) is not None


def _window_region(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region
    return None


def pass_override(context, area):
    """Build a temp_override dict for the gesture area/region."""
    window = None
    region = None
    if area is not None and _area_is_valid(area):
        window = _find_window_for_area(area)
        region = _window_region(area)
    if window is None:
        window = getattr(context, 'window', None)
    if region is None and getattr(context, 'region', None) is not None:
        region = context.region
    if window is None:
        return None

    override = {'window': window}
    if area is not None and _area_is_valid(area):
        override['area'] = area
    if region is not None:
        try:
            _ = region.type
            override['region'] = region
        except ReferenceError:
            ...
    return override


def invoke_operator_now(
        context,
        area,
        idname: str,
        properties: dict | None = None,
        *,
        operator_context: str = 'INVOKE_DEFAULT',
) -> bool:
    """Invoke an operator immediately (keeps mouse event / cursor position)."""
    override = pass_override(context, area)
    if override is None:
        return False
    properties = dict(properties or {})
    prefix, suffix = idname.split('.', 1)
    try:
        func = getattr(getattr(bpy.ops, prefix), suffix)
        with context.temp_override(**override):
            result = func(operator_context, True, **properties)
        debug_print(f"invoke now {idname}", properties, result, key='key')
        return bool({'FINISHED', 'CANCELLED', 'INTERFACE', 'RUNNING_MODAL'} & set(result))
    except Exception as exc:
        debug_print(f"invoke now {idname} error", exc.args, key='key')
        return False


def _needs_area_pin(idname: str) -> bool:
    """Deferred ops need the gesture area so ``context.space_data`` is valid.

    Timer callbacks otherwise run with a bare window context (area/space_data
    None), which breaks VIEW_3D operators (e.g. MACHIN3tools). Preferences /
    new-window ops must not pin — that steals OS focus from the new window.
    """
    if not idname:
        return False
    from .ui_filter import is_preferences_op
    if is_preferences_op(idname):
        return False
    return True


def defer_operator_call(
        context,
        area,
        idname: str,
        properties: dict | None = None,
        *,
        operator_context: str = 'INVOKE_DEFAULT',
        pin_area: bool | None = None,
) -> bool:
    """Schedule operator invocation after the modal handler finishes."""
    from .ui_filter import is_preferences_op

    override = pass_override(context, area)
    if override is None:
        return False

    properties = dict(properties or {})
    prefix, suffix = idname.split('.', 1)
    window = override.get('window')
    captured_area = override.get('area')
    captured_region = override.get('region')
    if pin_area is None:
        pin_area = _needs_area_pin(idname)
    is_prefs = is_preferences_op(idname)

    def _invoke(*_args):
        try:
            func = getattr(getattr(bpy.ops, prefix), suffix)
            # Preferences / new-window ops: do NOT pin gesture area/region —
            # that keeps input focus on the old View3D after the popup opens.
            # Still invoke even if Preferences already exists so it can refocus.
            if is_prefs or not pin_area:
                result = func(operator_context, True, **properties)
            else:
                ov = {'window': window}
                if captured_area is not None and _area_is_valid(captured_area):
                    ov['area'] = captured_area
                if captured_region is not None:
                    try:
                        _ = captured_region.type
                        ov['region'] = captured_region
                    except ReferenceError:
                        ...
                with context.temp_override(**ov):
                    result = func(operator_context, True, **properties)
            debug_print(f"deferred {idname}", properties, result, key='key')
        except Exception as exc:
            debug_print(f"deferred {idname} error", exc.args, key='key')
        return None

    bpy.app.timers.register(_invoke, first_interval=0)
    return True


def defer_gesture_element_operator(context, area, element) -> bool:
    """Defer a gesture element operator until after the modal returns FINISHED."""
    from ...element.element_operator import resolve_operator_bl_idname

    idname = resolve_operator_bl_idname(getattr(element, 'operator_bl_idname', '') or '')
    if not idname or '.' not in idname:
        return False
    props = getattr(element, 'properties', None)
    if not isinstance(props, dict):
        props = {}
    op_context = getattr(element, 'operator_context', None) or 'INVOKE_DEFAULT'
    return defer_operator_call(
        context,
        area,
        idname,
        props,
        operator_context=op_context,
    )


def check_kmi_pass_through(
        kmi: bpy.types.KeyMapItem,
        *,
        skip_ui_poll=False,
        ui_idnames=(),
        context=None,
        area=None,
) -> bool:
    if skip_ui_poll and kmi.idname in ui_idnames:
        return True
    prefix, suffix = kmi.idname.split('.')
    func = getattr(getattr(bpy.ops, prefix), suffix)
    if context is not None:
        override = pass_override(context, area)
        if override is not None:
            try:
                with context.temp_override(**override):
                    return bool(func.poll())
            except Exception:
                return False
    if not func.poll():
        return False
    return True


def defer_kmi_pass_through(context, area, kmi: bpy.types.KeyMapItem, ui_idnames=()) -> bool:
    """Schedule pass-through operator after modal ends; returns True if scheduled."""
    skip_ui_poll = kmi.idname in ui_idnames
    if not check_kmi_pass_through(
            kmi, skip_ui_poll=skip_ui_poll, ui_idnames=ui_idnames, context=context, area=area):
        debug_print("pass_through poll failed", kmi.idname, key='key')
        return False
    prop = get_kmi_operator_properties(kmi)
    return defer_operator_call(context, area, kmi.idname, prop)
