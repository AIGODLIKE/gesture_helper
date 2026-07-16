"""Gesture operator dispatch (execute path)."""

from __future__ import annotations

import bpy
from bpy.app.translations import pgettext

from .gesture_session import GestureSession, UiHandoff


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
                        pgettext(
                            "Operator not found, please check the operator id in gesture settings: %s"
                        )
                        % f"{name} -> {i.name} bpy.ops.{i.operator_bl_idname}",
                    )
                    return

            if i.check_operator_poll():
                idname = resolve_operator_bl_idname(i.operator_bl_idname)
                if i.operator_is_operator and should_defer_gesture_operator(idname):
                    area = getattr(session, 'area', None) or getattr(ops, 'area', None)
                    if defer_gesture_element_operator(bpy.context, area, i):
                        session.set_handoff(UiHandoff.DEFERRED)
                        ops.report({'INFO'}, i.name_translate)
                        return
                error = i.running_operator()
                if error is not None:
                    ops.report({'ERROR'}, pgettext("Operator error. Check the console for details."))
                    return
                ops.report({'INFO'}, i.name_translate)
            else:
                og = ops.operator_gesture
                name = og.name if og is not None else "?"
                ops.report(
                    {'ERROR'},
                    pgettext(
                        "Operator context error, please ensure that the operator is available in this context: %s"
                    )
                    % f"{name} -> {i.name} bpy.ops.{i.operator_bl_idname}.poll()",
                )

        snap = session.snapshot
        # Prefer extension-menu hover operators when the radial UI is up.
        if session.phase.shows_radial_ui and snap.extension_element and session.extension_hover:
            last = session.extension_hover[-1]
            for item in getattr(last, 'extension_items', []) or []:
                item.ops = ops
                if item.extension_by_child_is_hover and item.is_operator:
                    run(item)
                    return True
            # Panel / right band / child row block radial confirm — not vertical
            # travel (nested-menu tolerance; see extension_hit.BLOCKS_RADIAL).
            from ..element.extension_hit import stack_blocks_radial
            if stack_blocks_radial(session.extension_hover, ops):
                return False

        element = snap.direction_element
        if element and element.is_operator and (
                snap.threshold_zone.is_confirm or getattr(element, 'mouse_is_in_area', False)):
            run(element)
            return True
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
