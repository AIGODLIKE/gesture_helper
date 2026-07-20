"""Temporary keymap used for in-preferences key and operator property editing."""

from __future__ import annotations

import bpy

from .addon_keymap import get_kmi_operator_properties


def get_temp_keymap() -> bpy.types.KeyMap | None:
    window_manager = getattr(bpy.context, "window_manager", None)
    keyconfigs = getattr(window_manager, "keyconfigs", None)
    keyconfig = getattr(keyconfigs, "addon", None)
    if keyconfig is None:
        return None
    keymap = keyconfig.keymaps.get('TEMP')
    if keymap is None:
        keymap = keyconfig.keymaps.new('TEMP')
    return keymap


def clear_temp_keymap() -> None:
    keymap = get_temp_keymap()
    if keymap is None:
        return
    for kmi in list(keymap.keymap_items):
        keymap.keymap_items.remove(kmi)


def get_temp_kmi_by_id_name(id_name: str) -> bpy.types.KeyMapItem:
    keymap = get_temp_keymap()
    if keymap is None:
        raise RuntimeError("Add-on keyconfig is not available")
    keymap_items = keymap.keymap_items
    for kmi in keymap_items:
        if kmi.idname == id_name:
            return kmi
    return keymap_items.new(id_name, "NONE", "PRESS")


def get_temp_kmi(
        id_name: str,
        properties: dict,
        kmi_data=None,
) -> bpy.types.KeyMapItem:
    if kmi_data is None:
        kmi_data = {"type": "A", "value": "PRESS"}
    keymap = get_temp_keymap()
    if keymap is None:
        raise RuntimeError("Add-on keyconfig is not available")
    keymap_items = keymap.keymap_items
    for kmi in keymap_items:
        if kmi.idname == id_name:
            if kmi.properties is None:
                keymap_items.remove(kmi)
            elif get_kmi_operator_properties(kmi) == properties:
                return kmi
    kmi = keymap_items.new(id_name, **kmi_data)
    for key, value in properties.items():
        setattr(kmi.properties, key, value)
    return kmi


def draw_temp_keymap_item(
        layout: bpy.types.UILayout,
        kmi: bpy.types.KeyMapItem,
        key_maps: list[str],
) -> None:
    from ..ops import set_key
    from ..ops.restore_key import RestoreKey
    from ..utils.public import get_pref
    from ..utils.public_ui import icon_two

    layout.context_pointer_set('keymap', get_temp_keymap())

    gesture_property = get_pref().gesture_property
    show_expanded = gesture_property.show_gesture_keymaps
    show_icon = icon_two(show_expanded, 'TRIA')

    map_type = kmi.map_type
    col = layout.column()

    if show_expanded:
        col = col.column(align=True)
        box = col.box()
    else:
        box = col.column()

    split = box.split()

    row = split.row(align=True)
    row.prop(gesture_property, "show_gesture_keymaps", text="", emboss=False, icon=show_icon)
    row.row().operator(set_key.OperatorSetKeyMaps.bl_idname)

    row = split.row()
    row.prop(kmi, "map_type", text="")
    if map_type == 'KEYBOARD':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'MOUSE':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'NDOF':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'TWEAK':
        sub_row = row.row()
        sub_row.prop(kmi, "type", text="")
        sub_row.prop(kmi, "value", text="")
    elif map_type == 'TIMER':
        row.prop(kmi, "type", text="")
    else:
        row.label()

    row.operator(RestoreKey.bl_idname, text="", icon='BACK').item_id = kmi.id

    if show_expanded:
        box = col.box()
        if map_type not in {'TEXTINPUT', 'TIMER'}:
            sub = box.column()
            sub_row = sub.row(align=True)

            if map_type == 'KEYBOARD':
                sub_row.prop(kmi, "type", text="", event=True)
                sub_row.prop(kmi, "value", text="")
                sub_row_repeat = sub_row.row(align=True)
                sub_row_repeat.active = kmi.value in {'ANY', 'PRESS'}
                sub_row_repeat.prop(kmi, "repeat", text="Repeat")
            elif map_type in {'MOUSE', 'NDOF'}:
                sub_row.prop(kmi, "type", text="")
                sub_row.prop(kmi, "value", text="")

            if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
                sub_row = sub.row()
                sub_row.prop(kmi, "direction")

            sub_row = sub.row()
            sub_row.scale_x = 0.75
            sub_row.prop(kmi, "any", toggle=True)
            sub_row.prop(kmi, "shift_ui", toggle=True)
            sub_row.prop(kmi, "ctrl_ui", toggle=True)
            sub_row.prop(kmi, "alt_ui", toggle=True)
            sub_row.prop(kmi, "oskey_ui", text="Cmd", toggle=True)
            sub_row.prop(kmi, "key_modifier", text="", event=True)

        keymap_col = box.column(align=True)
        for keymap_name in key_maps:
            keymap_col.label(text=keymap_name)
