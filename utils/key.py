import bpy
from mathutils import Vector, Euler, Matrix


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


def get_addon_keymap(keymap) -> 'bpy.types.KeyMap':
    kk = bpy.context.window_manager.keyconfigs.addon.keymaps
    f = kk.get(keymap)
    if f:
        return f
    dk = bpy.context.window_manager.keyconfigs.default.keymaps.get(keymap)
    return kk.new(dk.name, space_type=dk.space_type, region_type=dk.region_type)


def add_addon_kmi(keymap, kmi_data, properties) -> ['bpy.types.KeyMap', 'bpy.types.KeyMapItem']:
    keymap = get_addon_keymap(keymap)
    kmi = keymap.keymap_items.new(**kmi_data)
    simple_set_property(properties, kmi.properties)
    return keymap, kmi
