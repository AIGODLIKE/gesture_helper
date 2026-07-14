"""Gesture operator dispatch (execute path)."""

from __future__ import annotations

import json
import time

import bpy

from .gesture_session import GestureSession, UiHandoff

# #region agent log
_DBG_LOG_PATHS = None


def _agent_dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None, *, run_id: str = "pre"):
    # Reuse input logger paths so verification lands in the same files.
    from .gesture_input import _agent_dbg as _input_dbg
    _input_dbg(hypothesis_id, location, message, data, run_id=run_id)
# #endregion


class GestureExecutor:
    """Run selected gesture element operators from session selection state."""

    def try_running_operator(self, session: GestureSession, ops) -> bool:
        """Try to run gesture operator(s). Returns True if an operator was attempted."""

        def run(i):
            from .pass_through import (
                defer_gesture_element_operator,
                should_defer_gesture_operator,
            )
            from ..element.element_operator import resolve_operator_bl_idname

            if i.operator_is_operator or i.operator_is_modal:
                if i.operator_func is None:
                    og = ops.operator_gesture
                    name = og.name if og is not None else "?"
                    ops.report(
                        {'ERROR'},
                        "Operator not found, please check the operator id in gesture settings "
                        f"{name} -> {i.name} bpy.ops.{i.operator_bl_idname}",
                    )
                    return

            if i.check_operator_poll():
                idname = resolve_operator_bl_idname(i.operator_bl_idname)
                from .pass_through.ui_filter import is_preferences_op

                is_prefs = is_preferences_op(idname)
                if i.operator_is_operator and should_defer_gesture_operator(idname):
                    area = getattr(session, 'area', None) or getattr(ops, 'area', None)
                    if defer_gesture_element_operator(bpy.context, area, i):
                        session.set_handoff(UiHandoff.DEFERRED)
                        return
                # Sync Preferences open must keep the user-click OS focus context.
                if is_prefs:
                    session.set_handoff(UiHandoff.OPENING_SYNC)
                error = i.running_operator()
                if error is not None:
                    if is_prefs:
                        session.clear_handoff()
                    ops.report({'ERROR'}, "Operator Run Error,Please check the console")
                    return
            else:
                og = ops.operator_gesture
                name = og.name if og is not None else "?"
                ops.report(
                    {'ERROR'},
                    "Operator context error, please ensure that the operator is available in this context "
                    f"{name} -> {i.name} bpy.ops.{i.operator_bl_idname}.poll()",
                )

        snap = session.snapshot
        # Prefer extension-menu hover operators when the radial UI is up.
        if session.phase.shows_radial_ui and snap.extension_element and session.extension_hover:
            last = session.extension_hover[-1]
            hover_hits = []
            for item in getattr(last, 'extension_items', []) or []:
                item.ops = ops
                hit = bool(item.extension_by_child_is_hover)
                area = getattr(item, "extension_by_child_draw_area", None)
                hover_hits.append({
                    "name": getattr(item, "name", None),
                    "is_op": bool(getattr(item, "is_operator", False)),
                    "hit": hit,
                    "area": list(area) if area else None,
                })
                if hit and item.is_operator:
                    # #region agent log
                    mx = getattr(getattr(ops, "event", None), "mouse_region_x", None)
                    my = getattr(getattr(ops, "event", None), "mouse_region_y", None)
                    _agent_dbg("C", "gesture_executor.py:ext_run", "run extension operator", {
                        "item": getattr(item, "name", None),
                        "mouse": [mx, my],
                        "hits": hover_hits,
                        "hover": [getattr(x, "name", str(x)) for x in session.extension_hover],
                    })
                    # #endregion
                    run(item)
                    return True
            # Mouse is over the extension panel but not an operator row —
            # do not fall through to radial direction confirm.
            in_extension = False
            for el in session.extension_hover:
                el.ops = ops
                if (
                        el.mouse_is_in_extension_area
                        or el.mouse_is_in_extension_vertical_outside_area
                        or el.mouse_is_in_extension_right_outside_area
                ):
                    in_extension = True
                    break
                for item in getattr(el, 'extension_items', []) or []:
                    item.ops = ops
                    if item.extension_by_child_is_hover:
                        in_extension = True
                        break
                if in_extension:
                    break
            # #region agent log
            mx = getattr(getattr(ops, "event", None), "mouse_region_x", None)
            my = getattr(getattr(ops, "event", None), "mouse_region_y", None)
            _agent_dbg("C", "gesture_executor.py:ext_miss", "extension path no op hit", {
                "in_extension": in_extension,
                "mouse": [mx, my],
                "hits": hover_hits,
                "hover": [getattr(x, "name", str(x)) for x in session.extension_hover],
                "ext_area": list(getattr(snap.extension_element, "extension_draw_area", None) or []) or None,
                "dir_el": getattr(snap.direction_element, "name", None),
                "zone": str(snap.threshold_zone),
            })
            # #endregion
            if in_extension:
                return False

        element = snap.direction_element
        if element and element.is_operator and (
                snap.threshold_zone.is_confirm or getattr(element, 'mouse_is_in_area', False)):
            # #region agent log
            _agent_dbg("C", "gesture_executor.py:dir_run", "run direction operator", {
                "element": getattr(element, "name", None),
                "dir": getattr(element, "direction", None),
                "zone": str(snap.threshold_zone),
                "hover_len": len(session.extension_hover),
                "phase": str(session.phase),
                "has_ext": bool(snap.extension_element),
            })
            # #endregion
            run(element)
            return True
        # #region agent log
        _agent_dbg("C", "gesture_executor.py:none", "no operator run", {
            "phase": str(session.phase),
            "has_ext": bool(snap.extension_element),
            "hover_len": len(session.extension_hover),
            "dir_el": getattr(snap.direction_element, "name", None),
            "zone": str(snap.threshold_zone),
        })
        # #endregion
        return False

    def try_immediate_implementation(self, session: GestureSession, ops) -> bool:
        """Try to run operator immediately when preference is enabled."""
        if not ops.gesture_property.immediate_implementation:
            return False
        snap = session.snapshot
        de = snap.direction_element
        if de and snap.threshold_zone.is_confirm and session.phase.shows_radial_ui:
            if de.is_operator:
                self.try_running_operator(session, ops)
                return True
        return False
