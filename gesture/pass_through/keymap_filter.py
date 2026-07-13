"""Keymap discovery + event match + blocklist (no allowlist)."""

from __future__ import annotations

from ...utils.debug_util import debug_print
from ..addon_keymap import get_kmi_operator_properties
from .ui_filter import PASS_THROUGH_UI_IDNAMES, filter_view3d_menu_kmis

# Do not re-enter gesture / related modal operators via pass-through.
# Include legacy ``gesture.operator`` — custom keyconfigs often keep both the
# old and new idnames; the legacy active item would otherwise shadow inactive
# RMB context menus (``active if active else inactive_ui``).
PASS_THROUGH_BLOCKLIST = frozenset({
    'wm.gesture_operator',
    'gesture.operator',
    'wm.gesture_modal_mouse_operator',
    'wm.gesture_element_modal_event',
    'wm.gesture_temp_kmi',
    'wm.gesture_preview',
})

OBJECT_MODE_MAP = {
    "OBJECT": "Object Mode",
    "SCULPT": "Sculpt",
    "PAINT_VERTEX": "Vertex Paint",
    "PAINT_WEIGHT": "Weight Paint",
    "PAINT_TEXTURE": "Image Paint",
    "EDIT_MESH": "Mesh",
    "EDIT_LATTICE": "Lattice",
    "EDIT_ARMATURE": "Armature",
    "EDIT_TEXT": "Font",
    "EDIT_METABALL": "Metaball",
    "EDIT_SURFACE": "Curve",
    "EDIT_CURVE": "Curve",
    "EDIT_CURVES": "Curves",
    "SCULPT_CURVES": "Sculpt Curves",
    "POSE": "Pose",
    "PARTICLE": "Particle",
    "EDIT_GREASE_PENCIL": "Grease Pencil Edit Mode",
    "SCULPT_GREASE_PENCIL": "Grease Pencil Sculpt Mode",
    "PAINT_GREASE_PENCIL": "Grease Pencil Paint Mode",
    "WEIGHT_GREASE_PENCIL": "Grease Pencil Weight Paint",
}

AREA_MAP = {
    "VIEW_3D": "3D View",
    "IMAGE_EDITOR": "Image",
    "NODE_EDITOR": "Node Editor",
    "DOPESHEET_EDITOR": "Dopesheet",
    "GRAPH_EDITOR": "Graph Editor",
    "NLA_EDITOR": "NLA Editor",
    "SPREADSHEET": "Spreadsheet Generic",
    "TEXT_EDITOR": "Text",
    "CONSOLE": "Console",
    "INFO": "Info",
    "OUTLINER": "Outliner",
    "PROPERTIES": "Property Editor",
    "FILE_BROWSER": "File Browser",
}

SEQUENCE_MAP = {
    "SEQUENCER": "Sequencer",
    "PREVIEW": "SequencerPreview",
}

SEQUENCER_PREVIEW_MAP = {
    "PREVIEW": "SequencerPreview",
    "WINDOW": "Sequencer",
}

TRACKING_MAP = {
    "CLIP": "Clip Editor",
    "GRAPH": "Clip Graph Editor",
    "DOPESHEET": "Clip Dopesheet Editor",
}

IMAGE_UI_MODE_MAP = {
    "VIEW": "Image",
    "PAINT": "Image Paint",
    "MASK": "Mask Editing",
}


def kmi_matches_event(event, kmi) -> bool:
    event_type = event.type
    kmi_type = kmi.type
    if event_type != kmi_type:
        if not (event_type in {'RIGHTMOUSE', 'APP'} and kmi_type in {'RIGHTMOUSE', 'APP'}):
            return False

    if not kmi.any:
        if bool(kmi.shift) != event.shift:
            return False
        if bool(kmi.ctrl) != event.ctrl:
            return False
        if bool(kmi.alt) != event.alt:
            return False
        if bool(getattr(kmi, 'oskey', False)) != bool(getattr(event, 'oskey', False)):
            return False

    if kmi.value not in {'NOTHING', 'ANY'} and event.value != kmi.value:
        # Gesture modal consumes PRESS and exits on RELEASE.
        if not (event.value == 'RELEASE' and kmi.value == 'PRESS'):
            return False
    return True


def match_kmis_in_keymap(km, event, ui_idnames=PASS_THROUGH_UI_IDNAMES):
    """Match event against keymap items; blocklist only (no allowlist)."""
    active = []
    inactive_ui = []
    for item in km.keymap_items:
        if not item.idname or item.idname in PASS_THROUGH_BLOCKLIST:
            continue
        if not kmi_matches_event(event, item):
            continue
        if item.active:
            active.append(item)
        elif item.idname in ui_idnames:
            inactive_ui.append(item)
    # RMB/APP: custom keymaps often disable the context menu while leaving
    # unrelated active bindings. Prefer inactive UI when no active UI remains.
    if active:
        if (
                event.type in {'RIGHTMOUSE', 'APP'}
                and inactive_ui
                and not any(item.idname in ui_idnames for item in active)
        ):
            return inactive_ui
        return active
    return inactive_ui


def apply_user_keymap_overrides(match_kmis, key, user_keymaps):
    if key not in user_keymaps or not match_kmis:
        return match_kmis
    for index, match_kmi in enumerate(match_kmis):
        for kmi in user_keymaps[key].keymap_items:
            props_ok = get_kmi_operator_properties(kmi) == get_kmi_operator_properties(match_kmi)
            if kmi.idname == match_kmi.idname and props_ok and kmi.is_user_modified:
                match_kmis[index] = kmi
    return match_kmis


def from_region_get_keymaps(context) -> list[str]:
    """Keymap names relevant to the current area/region/mode."""
    area_type = context.area.type
    region_type = context.region.type
    keymaps = context.window_manager.keyconfigs.active.keymaps

    view_type = getattr(context.space_data, "view_type", None)
    mode = getattr(context.space_data, "mode", None)
    view = getattr(context.space_data, "view", None)

    mk = AREA_MAP.get(area_type)
    keys = []

    if area_type == "VIEW_3D":
        keys.append("3D View Generic")
        mode_key = OBJECT_MODE_MAP.get(context.mode)
        if mode_key:
            keys.append(mode_key)
        else:
            obj = context.object
            if obj and obj.type == "CURVES":
                keys.append("Curves")
    elif area_type == "SEQUENCE_EDITOR":
        sequence = SEQUENCE_MAP.get(view_type)
        if sequence is not None:
            keys.append(sequence)
        if view_type == "SEQUENCER_PREVIEW":
            keys.append(SEQUENCER_PREVIEW_MAP.get(region_type))
    elif area_type == "CLIP_EDITOR":
        if mode == "TRACKING":
            t = TRACKING_MAP.get(view)
            if t is not None:
                keys.append(t)
        elif mode == "MASK":
            keys.append("Clip Editor")
    elif area_type == "IMAGE_EDITOR":
        ut = context.area.ui_type
        ui_mode = getattr(context.space_data, "ui_mode", None)
        if ut == "UV":
            keys.append("UV Editor")
        elif ut == "IMAGE_EDITOR":
            if ui_mode and ui_mode in IMAGE_UI_MODE_MAP:
                keys.append(IMAGE_UI_MODE_MAP.get(ui_mode))
        keys.append("Image Generic")
        debug_print(ut, ui_mode, key='key')

    if mk is not None:
        keys.append(mk)
    else:
        for k in keymaps.keys():
            if k.lower() == context.mode.lower():
                keys.append(k)

    keys.append("Window")
    return [key for key in keys if key]


def collect_pass_kmis(context, event, keys, keymaps, user_keymaps):
    """Collect matching KMIs from *keys*; apply View3D menu filter for RMB/APP."""
    matched = []
    for key in keys:
        if key not in keymaps:
            continue
        km = keymaps[key]
        match_kmis = match_kmis_in_keymap(km, event)
        match_kmis = apply_user_keymap_overrides(match_kmis, key, user_keymaps)
        if match_kmis:
            debug_print(
                "try_pass_through_keymap match",
                key,
                [i.idname for i in match_kmis],
                key='key',
            )
            matched.extend(match_kmis)
    if not matched:
        return []
    if event is not None and event.type in {'RIGHTMOUSE', 'APP'}:
        return filter_view3d_menu_kmis(context, matched)
    return matched
