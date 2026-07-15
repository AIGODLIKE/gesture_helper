"""UI / menu pass-through filters (RMB context menus, defer UI operators)."""

from __future__ import annotations

from ..addon_keymap import get_kmi_operator_properties

PASS_THROUGH_UI_IDNAMES = (
    'wm.call_menu',
    'wm.call_panel',
    'wm.call_menu_pie',
    'wm.call_menu_pie_drag_only',
)

# Operators that open UI while the gesture modal is still on the stack.
_DEFER_GESTURE_OPERATOR_IDNAMES = frozenset({
    'wm.call_menu',
    'wm.call_panel',
    'wm.call_menu_pie',
    'wm.call_menu_pie_drag_only',
    'wm.search_menu',
    'wm.search_operator',
    'wm.search_single_menu',
})

_VIEW3D_CONTEXT_MENUS = {
    'OBJECT': 'VIEW3D_MT_object_context_menu',
    'EDIT_MESH': 'VIEW3D_MT_edit_mesh_context_menu',
    'EDIT_CURVE': 'VIEW3D_MT_edit_curve_context_menu',
    'EDIT_SURFACE': 'VIEW3D_MT_edit_curve_context_menu',
    'EDIT_CURVES': 'VIEW3D_MT_edit_curves_context_menu',
    'SCULPT_CURVES': 'VIEW3D_MT_sculpt_curves_context_menu',
    'EDIT_ARMATURE': 'VIEW3D_MT_armature_context_menu',
    'POSE': 'VIEW3D_MT_pose_context_menu',
    'SCULPT': 'VIEW3D_MT_sculpt_context_menu',
    'PAINT_WEIGHT': 'VIEW3D_MT_paint_weight_context_menu',
    'PAINT_VERTEX': 'VIEW3D_MT_paint_vertex_context_menu',
    'PAINT_TEXTURE': 'VIEW3D_MT_paint_texture_context_menu',
    'PARTICLE': 'VIEW3D_MT_particle_context_menu',
    'EDIT_METABALL': 'VIEW3D_MT_edit_metaball_context_menu',
    'EDIT_LATTICE': 'VIEW3D_MT_edit_lattice_context_menu',
    'EDIT_TEXT': 'VIEW3D_MT_edit_font_context_menu',
    'EDIT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'SCULPT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'PAINT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'WEIGHT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
}


# Operators that must keep the current mouse/event (sync invoke in exit).
_SYNC_GESTURE_OPERATOR_PREFIXES = (
    'transform.',
)


# Built-ins that open a Preferences OS window — stay sync (not deferred).
_SYNC_WINDOW_OPEN_IDNAMES = frozenset({
    'screen.userpref_show',
    'preferences.addon_show',
})


def should_defer_gesture_operator(idname: str) -> bool:
    """Return True if *idname* should run after the gesture modal exits.

    Only defer known UI openers (menus/panels/search). Normal operators such as
    ``wm.context_toggle`` / panel switching must stay sync so they keep area
    context. Built-in Preferences openers stay sync.
    """
    if not idname:
        return False
    if idname.startswith(_SYNC_GESTURE_OPERATOR_PREFIXES):
        return False
    if idname in _SYNC_WINDOW_OPEN_IDNAMES:
        return False
    if idname in _DEFER_GESTURE_OPERATOR_IDNAMES:
        return True
    if idname.startswith('wm.call_'):
        return True
    return False


def is_ui_pass_idname(idname: str) -> bool:
    return idname in PASS_THROUGH_UI_IDNAMES


def expected_view3d_menu(context) -> str | None:
    area = context.area
    if area is None or area.type != 'VIEW_3D':
        return None
    return _VIEW3D_CONTEXT_MENUS.get(context.mode)


def filter_view3d_menu_kmis(context, match_kmis):
    """Prefer the View3D *context* menu for the current mode (RMB/APP only).

    Do NOT run this for keyboard keys: Edit Mode X/M bind ``wm.call_menu`` to
    delete/merge menus, not ``VIEW3D_MT_*_context_menu``.
    """
    expected = expected_view3d_menu(context)
    if not expected:
        return match_kmis

    call_menus = [kmi for kmi in match_kmis if kmi.idname == 'wm.call_menu']
    if not call_menus:
        return match_kmis

    matched_menus = [
        kmi for kmi in call_menus
        if get_kmi_operator_properties(kmi).get('name') == expected
    ]
    other = [kmi for kmi in match_kmis if kmi.idname != 'wm.call_menu']
    if matched_menus:
        return matched_menus + other
    return other


def should_pass_rmb_ui(event) -> bool:
    """RMB context menus only on a plain near-click, not modifiers."""
    if event.type not in {'RIGHTMOUSE', 'APP'}:
        return True
    if event.shift or event.ctrl or event.alt or getattr(event, 'oskey', False):
        return False
    return True
