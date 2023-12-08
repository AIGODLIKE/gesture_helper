from functools import cache

import bpy
from mathutils import Vector, Euler, Matrix

from . import PropertyGetUtils


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
        if temp_kmi.properties == None:
            keymap_items.remove(temp_kmi)
        elif get_kmi_operator_properties(temp_kmi) == properties:
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
    del_key = []
    for item in dictionary:
        prop = getattr(properties, item, None)
        typ = type(prop)
        if prop:
            if prop and typ == Vector:
                # 属性阵列-浮点数组
                dictionary[item] = dictionary[item].to_tuple()
            elif prop and typ == Euler:
                dictionary[item] = dictionary[item][:]
            elif prop and typ == Matrix:
                dictionary[item] = tuple(i[:] for i in dictionary[item])
            elif typ == bpy.types.bpy_prop_array:
                dictionary[item] = dictionary[item][:]
            elif typ in (str, bool, float, int, set, list, tuple):
                ...
            elif typ.__name__ in [
                'TRANSFORM_OT_shrink_fatten',
                'TRANSFORM_OT_translate',
                'TRANSFORM_OT_edge_slide',
                'NLA_OT_duplicate',
                'ACTION_OT_duplicate',
                'GRAPH_OT_duplicate',
                'TRANSFORM_OT_translate',
                'OBJECT_OT_duplicate',
                'MESH_OT_loopcut',
                'MESH_OT_rip_edge',
                'MESH_OT_duplicate',
                'MESH_OT_offset_edge_loops',
                'MESH_OT_extrude_faces_indiv',
            ]:
                ...
            else:
                print('emm 未知属性,', typ, dictionary[item])
                del_key.append(item)
    for i in del_key:
        dictionary.pop(i)
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


def add_addon_kmi(keymap_name, kmi_data, properties) -> ['bpy.types.KeyMap', 'bpy.types.KeyMapItem']:
    keymap = get_addon_keymap(keymap_name)
    handle_conflicting_keymaps(keymap_name, kmi_data.copy())
    kmi = keymap.keymap_items.new(**kmi_data)
    simple_set_property(properties, kmi.properties)
    return keymap, kmi


def handle_conflicting_keymaps(keymap_name, kmi_data):
    kc = bpy.context.window_manager.keyconfigs
    keymap = kc.user.keymaps.get(keymap_name, None)
    kmi_data.pop('idname')

    if keymap:
        for kmi in keymap.keymap_items:
            kmi_props = PropertyGetUtils.kmi_props(kmi)
            is_equal_kmi = kmi_props == kmi_data  # 触发键一样
            is_menu = kmi.idname in ('wm.call_menu', 'wm.call_panel', 'wm.call_menu_pie', 'object.delete')  # 是弹出菜单
            is_press = 'value' in kmi_props and kmi_props['value'] == 'PRESS'  # 是按下触发
            not_is_left_mouse = 'type' in kmi_props and kmi_props['type'] != 'LEFTMOUSE'  # 如果是左键不能替换
            is_x = 'type' in kmi_props and kmi_props['type'] == 'X'  # 如果是删除的按键

            if is_equal_kmi and is_menu and is_press and (not_is_left_mouse or is_x):
                kmi.value = 'RELEASE'

                # print('handle_conflicting_keymaps')
                # print('keymap', keymap)
                # print('kmi_data', kmi_data)
                # print(is_equal_kmi, is_menu, is_press, kmi.idname, kmi_props)
                # print()


def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy', key_maps):
    from ..ops import set_key
    from .public import get_pref
    from .public_ui import icon_two

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

    # header bar
    row = split.row(align=True)
    row.prop(gesture_property, "show_gesture_keymaps", text="", emboss=False, icon=show_icon)

    # row.prop(kmi, "active", text="", emboss=False)
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

    from ..ops.restore_key import RestoreKey
    row.operator(RestoreKey.bl_idname, text="", icon='BACK').item_id = kmi.id
    # Expanded, additional event settings
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
            # Use `*_ui` properties as integers aren't practical.
            sub_row.prop(kmi, "shift_ui", toggle=True)
            sub_row.prop(kmi, "ctrl_ui", toggle=True)
            sub_row.prop(kmi, "alt_ui", toggle=True)
            sub_row.prop(kmi, "oskey_ui", text="Cmd", toggle=True)

            sub_row.prop(kmi, "key_modifier", text="", event=True)

        col = box.column(align=True)
        for k in key_maps:
            col.label(text=k)
