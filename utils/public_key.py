from functools import cache

import bpy
from mathutils import Vector, Euler, Matrix


def get_temp_kmi_by_id_name(id_name: str) -> 'bpy.types.KeyMapItem':
    keymap_items = get_temp_keymap().keymap_items
    for temp_kmi in keymap_items:
        if temp_kmi.idname == id_name:
            return temp_kmi
    return keymap_items.new(id_name, "NONE", "PRESS")


def simple_set_property(prop, to):
    for k, v in prop.items():  # TIPS简单的赋值,这个属性在这里只有字符串,所以可以这样弄
        setattr(to, k, v)


def get_temp_keymap():
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    return keyconfig.keymaps.get('TEMP', keyconfig.keymaps.new('TEMP'))


def get_temp_kmi(id_name: str, properties: dict) -> 'bpy.types.KeyMapItem':
    """
    bpy.context.window_manager.keyconfigs.active.keymaps['TEMP'].keymap_items
    @return:
    """
    keymap_items = get_temp_keymap().keymap_items
    for temp_kmi in keymap_items:
        if get_kmi_operator_properties(temp_kmi) == properties:
            return temp_kmi

    kmi = keymap_items.new(id_name, "NONE", "PRESS")
    simple_set_property(properties, kmi.properties)
    return kmi


def get_kmi_operator_properties(kmi: 'bpy.types.KeyMapItem'):
    """获取kmi操作符的属性
    """
    properties = kmi.properties
    prop_keys = dict(properties.items()).keys()
    dictionary = {i: getattr(properties, i, None) for i in prop_keys}
    for item in dictionary:
        prop = getattr(properties, item, None)
        typ = type(prop)
        if prop and typ == Vector:
            # 属性阵列-浮点数组
            dictionary[item] = dictionary[item].to_tuple()
        elif prop and typ == Euler:
            dictionary[item] = dictionary[item][:]
        elif prop and typ == Matrix:
            dictionary[item] = tuple(i[:] for i in dictionary[item])
    return dictionary


@cache
def get_addon_keymap(keymap) -> 'bpy.types.KeyMap':
    kf = bpy.context.window_manager.keyconfigs
    kk = kf.addon.keymaps
    find = kk.get(keymap)
    if find:
        return find
    dk = kf.default.keymaps.get(keymap)
    if dk:
        return kk.new(dk.name, space_type=dk.space_type, region_type=dk.region_type)
    else:
        return kk.new(keymap, space_type='EMPTY', region_type='WINDOW')


def add_addon_kmi(keymap, kmi_data, properties) -> ['bpy.types.KeyMap', 'bpy.types.KeyMapItem']:
    keymap = get_addon_keymap(keymap)
    kmi = keymap.keymap_items.new(**kmi_data)
    simple_set_property(properties, kmi.properties)
    return keymap, kmi


def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy', key_maps):
    from ..ops import set_key
    map_type = kmi.map_type

    col = layout.column()

    if kmi.show_expanded:
        col = col.column(align=True)
        box = col.box()
    else:
        box = col.column()

    split = box.split()

    # header bar
    row = split.row(align=True)
    row.prop(kmi, "show_expanded", text="", emboss=False)
    # row.prop(kmi, "active", text="", emboss=False)
    row.operator(set_key.OperatorSetKeyMaps.bl_idname)

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

    row.operator("preferences.keyitem_restore", text="", icon='BACK').item_id = kmi.id
    # Expanded, additional event settings
    if kmi.show_expanded:
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
            # Use `*_ui` properties as integers aren't practical.
            sub_row.prop(kmi, "shift_ui", toggle=True)
            sub_row.prop(kmi, "ctrl_ui", toggle=True)
            sub_row.prop(kmi, "alt_ui", toggle=True)
            sub_row.prop(kmi, "oskey_ui", text="Cmd", toggle=True)

            sub_row.prop(kmi, "key_modifier", text="", event=True)

        col = box.column(align=True)
        for k in key_maps:
            col.label(text=k)
