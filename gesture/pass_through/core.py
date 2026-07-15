"""Gesture keymap pass-through orchestration.

HARD RULE (do not re-introduce RMB exceptions in ops/gesture.py):
    - Gesture shown (timeout or draw) → no pass
    - Dragged beyond threshold → no pass
    Pass only for a near-click that never showed the gesture UI.
"""

from __future__ import annotations

import bpy

from ...utils.debug_util import debug_print
from ..addon_keymap import get_kmi_operator_properties
from . import cursor
from .invoke import defer_kmi_pass_through, defer_operator_call, invoke_operator_now
from .keymap_filter import collect_pass_kmis, from_region_get_keymaps
from .ui_filter import (
    PASS_THROUGH_UI_IDNAMES,
    expected_view3d_menu,
    is_ui_pass_idname,
    should_defer_gesture_operator,
    should_pass_rmb_ui,
)


class GesturePassThroughKeymap:
    """Mixin: gate + match + priority pass for near-click shortcuts."""

    # Kept for callers that still reference the class attribute.
    pass_through_ui_idname = PASS_THROUGH_UI_IDNAMES

    def get_keymaps(self, context, event=None):
        """Always use region-relevant keymaps (no pass_through_keymap_type)."""
        return from_region_get_keymaps(context)

    def can_pass_through_keymap(self, event=None) -> bool:
        """Whether keymap pass-through is allowed for this gesture session.

        HARD RULE — do not weaken for RMB / Shift+RMB / APP / timeout edge cases:

        - After the gesture UI is shown (timeout or draw) → **no pass**
        - After the mouse is dragged beyond the threshold → **no pass**
        """
        session = getattr(self, 'session', None)
        if session is None:
            return False
        if session.phase.shows_radial_ui:
            debug_print("can_pass_through_keymap: blocked (gesture drawn/timeout)", key='key')
            return False
        snap = getattr(session, 'snapshot', None)
        if snap is not None and snap.threshold_zone.is_beyond:
            debug_print("can_pass_through_keymap: blocked (beyond threshold)", key='key')
            return False
        return True

    def _pass_matched_kmis(self, context, area, event, match_kmis) -> bool:
        """
        Priority:
        1. Shift+RMB cursor (sync)
        2. Plain RMB/APP → UI menus (defer)
        3. Other matched operators (defer if needed, else sync)
        """
        if not match_kmis:
            return False

        for kmi in match_kmis:
            if cursor.try_pass_set_cursor3d_location(self, context, event, kmi, area):
                return True

        allow_ui = should_pass_rmb_ui(event)
        ui_kmis = [
            kmi for kmi in match_kmis
            if is_ui_pass_idname(kmi.idname)
        ] if allow_ui else []
        non_ui_kmis = [
            kmi for kmi in match_kmis
            if not is_ui_pass_idname(kmi.idname)
            and not cursor.is_cursor_transform_kmi(kmi)
        ]
        candidates = ui_kmis if ui_kmis else non_ui_kmis

        for kmi in candidates:
            if not (kmi.active or is_ui_pass_idname(kmi.idname)):
                continue
            if is_ui_pass_idname(kmi.idname) or should_defer_gesture_operator(kmi.idname):
                if defer_kmi_pass_through(context, area, kmi, PASS_THROUGH_UI_IDNAMES):
                    return True
            else:
                session = getattr(self, 'session', None)
                props = get_kmi_operator_properties(kmi)
                if session is not None:
                    from .window_focus import begin_sync_op, end_sync_op
                    begin_sync_op(session)
                    ok = invoke_operator_now(context, area, kmi.idname, props)
                    if ok:
                        end_sync_op(session)
                    else:
                        session.clear_handoff()
                    if ok:
                        return True
                elif invoke_operator_now(context, area, kmi.idname, props):
                    return True
        return False

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> str | None:
        """Try to pass through key events. Returns ``'handled'`` or ``None``."""
        if not self.can_pass_through_keymap(event):
            return None

        gesture_area = getattr(self, 'area', None) or context.area
        keys = self.get_keymaps(context, event)
        kc = context.window_manager.keyconfigs
        debug_print("try_pass_through_keymap keys", keys, key='key')
        match_kmis = collect_pass_kmis(context, event, keys, kc.active.keymaps, kc.user.keymaps)
        debug_print(
            "try_pass_through_keymap matched",
            [(kmi.idname, get_kmi_operator_properties(kmi)) for kmi in match_kmis],
            key='key',
        )

        if match_kmis and self._pass_matched_kmis(context, gesture_area, event, match_kmis):
            return 'handled'

        # v2.3.3 RMB safety net: if keymap match missed the (often inactive)
        # context menu, still open the mode-appropriate View3D menu.
        expected_menu = expected_view3d_menu(context)
        if (
                event.type in {'RIGHTMOUSE', 'APP'}
                and should_pass_rmb_ui(event)
                and expected_menu
        ):
            if defer_operator_call(
                    context, gesture_area, 'wm.call_menu', {'name': expected_menu}):
                return 'handled'
        return None

    @staticmethod
    def try_pass_annotations_eraser(context: bpy.types.Context, event: bpy.types.Event) -> set | None:
        if context.space_data and context.space_data.type in ("VIEW_3D", "NODE_EDITOR"):
            if context.active_annotation_layer:
                if (event.type, event.type_prev) in [
                    ('D', 'RIGHTMOUSE'),
                    ('RIGHTMOUSE', 'D'),
                    ('MOUSEMOVE', 'D'),
                    ('D', 'D')
                ]:
                    return {'FINISHED', 'PASS_THROUGH'}
        return None

    @staticmethod
    def try_pass_paint_texture_stencil(context: bpy.types.Context, event: bpy.types.Event) -> set | None:
        from bl_ui.properties_paint_common import UnifiedPaintPanel

        settings = UnifiedPaintPanel.paint_settings(context)
        brush = getattr(settings, "brush", None)
        if context.space_data and context.space_data.type == "VIEW_3D":
            if context.mode == "PAINT_TEXTURE" and brush:
                ts = getattr(brush, "texture_slot", None)
                if ts and getattr(ts, "map_mode", None) == "STENCIL":
                    if event.type == "RIGHTMOUSE":
                        return {'FINISHED', 'PASS_THROUGH'}
        return None
