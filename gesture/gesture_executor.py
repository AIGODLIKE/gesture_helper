"""Gesture operator dispatch (execute path)."""

from __future__ import annotations

import bpy
from bpy.app.translations import pgettext

from .gesture_session import GestureSession, UiHandoff


class GestureExecutor:
    """Run selected gesture element operators from session selection state."""

    @staticmethod
    def _run_property_element(ops, element) -> None:
        """Property row action: toggle in place, or start the value-drag modal."""
        prop_type = element.display_property_type
        if prop_type is None:
            ops.report(
                {'ERROR'},
                pgettext("Property path not found: %s") % element.property_data_path,
            )
            return
        if not element.display_property_is_editable:
            ops.report(
                {'ERROR'},
                pgettext("Cannot change this property: %s") % element.property_data_path,
            )
            return
        if prop_type in {'BOOLEAN', 'ENUM'}:
            if element.toggle_display_property():
                ops.report({'INFO'}, element.display_property_text)
            else:
                ops.report(
                    {'ERROR'},
                    pgettext("Cannot change this property: %s") % element.property_data_path,
                )
            return
        if prop_type in {'INT', 'FLOAT'}:
            func = bpy.ops.wm.gesture_modal_mouse_operator
            if func.poll():
                func(
                    'INVOKE_DEFAULT', True,
                    data_path=element.property_context_path,
                    value_mode='MOUSE_CHANGES_HORIZONTAL',
                )
                ops.report({'INFO'}, element.name_translate)
            return
        ops.report(
            {'ERROR'},
            pgettext("This property type cannot be changed from a gesture: %s") % prop_type,
        )

    def try_running_operator(self, session: GestureSession, ops) -> bool:
        """Try to run gesture operator(s). Returns True if an operator was attempted."""

        def run(i, depth=0):
            from .pass_through import (
                defer_gesture_element_operator,
                should_defer_gesture_operator,
            )
            from ..element.element_operator import resolve_operator_bl_idname

            if i.is_property_display:
                self._run_property_element(ops, i)
                return
            if i.is_layout_container:
                # Layout nodes are presentation-only.  Their operator/property
                # leaves are dispatched from the hovered panel row instead of
                # treating the container as a hidden "main action".
                return

            if i.operator_is_operator or i.operator_is_modal:
                if i.operator_func is None:
                    og = ops.operator_gesture
                    name = og.name if og is not None else "?"
                    ops.report(
                        {'ERROR'},
                        pgettext(
                            "Operator not found. Check the operator ID in gesture settings: %s"
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
                        "Operator unavailable in this context: %s"
                    )
                    % f"{name} -> {i.name} bpy.ops.{i.operator_bl_idname}.poll()",
                )

        snap = session.snapshot
        # Prefer panel-row hover actions when the radial UI is up.
        if session.phase.shows_radial_ui and session.extension_hover:
            last = session.extension_hover[-1]
            if last.is_layout_container:
                items = last.panel_leaf_items
            else:
                items = getattr(last, 'extension_items', []) or []
            for item in items:
                item.ops = ops
                if not item.extension_by_child_is_hover:
                    continue
                if item.is_property_display and session._suppress_property_execute:
                    # Value drag already applied on this event; exit quietly
                    # (stack still blocks the radial confirm below).
                    session._suppress_property_execute = False
                    break
                if item.is_operator or item.is_property_display:
                    run(item)
                    return True
            # Panel / right band / child row block radial confirm — not vertical
            # travel (nested-menu tolerance; see extension_hit.BLOCKS_RADIAL).
            from ..element.extension_hit import stack_blocks_radial
            if stack_blocks_radial(session.extension_hover, ops):
                return False

        element = snap.direction_element
        runnable = element is not None and (element.is_operator or element.is_property_display)
        if runnable and (
                snap.threshold_zone.is_confirm or getattr(element, 'mouse_is_in_area', False)):
            # In-gesture INT/FLOAT scrub already applied the value — do not
            # launch the post-exit modal mouse operator again.
            if element.is_property_display and session._suppress_property_execute:
                session._suppress_property_execute = False
                return True
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
