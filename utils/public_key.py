import bpy
from mathutils import Vector, Euler, Matrix


def get_temp_kmi_by_id_name(id_name: str) -> 'bpy.types.KeyMapItem':
    keymap_items = get_temp_keymap().keymap_items
    for temp_kmi in keymap_items:
        if temp_kmi.idname == id_name:
            return temp_kmi
    return keymap_items.new(id_name, "NONE", "PRESS")


def simple_set_property(prop, to) -> None:
    for k, v in prop.items():  # TIPS简单的赋值,这个属性在这里只有字符串,所以可以这样弄
        setattr(to, k, v)


def get_temp_keymap() -> 'bpy.types.KeyMap':
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    return keyconfig.keymaps.get('TEMP', keyconfig.keymaps.new('TEMP'))


def get_temp_kmi(id_name: str, properties: dict) -> 'bpy.types.KeyMapItem':
    """
    bpy.context.window_manager.keyconfigs.active.keymaps['TEMP'].keymap_items
    @return:
    """
    keymap_items = get_temp_keymap().keymap_items
    for temp_kmi in keymap_items:
        if temp_kmi.properties is None:
            keymap_items.remove(temp_kmi)
        elif get_kmi_operator_properties(temp_kmi) == properties:
            return temp_kmi

    kmi = keymap_items.new(id_name, "NONE", "PRESS")
    simple_set_property(properties, kmi.properties)
    return kmi


def get_kmi_operator_properties(kmi: 'bpy.types.KeyMapItem') -> dict:
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
            if typ == Vector:
                # 属性阵列-浮点数组
                dictionary[item] = dictionary[item].to_tuple()
            elif typ == Euler:
                dictionary[item] = dictionary[item][:]
            elif typ == Matrix:
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
                'MESH_OT_rip',
                'MESH_OT_duplicate',
                'MESH_OT_offset_edge_loops',
                'MESH_OT_extrude_faces_indiv',
            ]:  # 一些奇怪的操作符属性,不太好解析也用不上
                ...
                del_key.append(item)
            else:
                print('emm 未知属性,', typ, dictionary[item])
                del_key.append(item)
    for i in del_key:
        dictionary.pop(i)
    return dictionary


def get_addon_keymap(keymap: str) -> 'bpy.types.KeyMap':
    kc = bpy.context.window_manager.keyconfigs
    keymaps = kc.addon.keymaps
    find = keymaps.get(keymap)
    if find:
        return find
    km = kc.active.keymaps.get(keymap)
    if km:
        return keymaps.new(km.name, space_type=km.space_type, region_type=km.region_type)
    else:
        return keymaps.new(keymap, space_type='EMPTY', region_type='WINDOW')


def find_kmi() -> ["bpy.types.KeyMap", "bpy.types.KeyMapItem"]:
    """查找addon快捷键下的操作符
    # for kc in [kcs.user, kcs.addon, kcs.default, kcs.active]:
    """
    from ..ops.gesture import GestureOperator
    id_name = GestureOperator.bl_idname
    kcs = bpy.context.window_manager.keyconfigs

    for km in kcs.addon.keymaps.values():
        kmi_item = km.keymap_items.find_from_operator(id_name)
        if kmi_item:
            return km, kmi_item
        kmi_index = km.keymap_items.find(id_name)
        if kmi_index != -1:
            return km, km.keymap_items[kmi_index]
        for kmi in km.keymap_items:
            if kmi.idname == id_name:
                return km, kmi
    return None, None


def add_addon_kmi(keymap_name, kmi_data, properties) -> ['bpy.types.KeyMap', 'bpy.types.KeyMapItem']:
    keymap = get_addon_keymap(keymap_name)
    kmi = keymap.keymap_items.new(**kmi_data)
    simple_set_property(properties, kmi.properties)
    return keymap, kmi


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
