from functools import cache

import bpy
from mathutils import Vector, Euler, Matrix


@cache
def get_temp_kmi(id_name: str, properties: dict):
    """
    bpy.context.window_manager.keyconfigs.active.keymaps['TEMP'].keymap_items
    @param properties:
    @param id_name:
    @return:
    """
    keyconfig = bpy.context.window_manager.keyconfigs.active
    temp_keymaps = keyconfig.keymaps.get('TEMP', keyconfig.keymaps.new('TEMP'))
    keymap_items = temp_keymaps.keymap_items
    for temp_kmi in keymap_items:
        if get_kmi_operator_properties(temp_kmi) == properties:
            return temp_kmi

    kmi = keymap_items.new(id_name, "NONE", "PRESS")
    for k, v in properties:  # TIPS简单的赋值,这个属性在这里只有字符串,所以可以这样弄
        setattr(kmi.properties, k, v)
    return kmi


def get_kmi_operator_properties(kmi: 'bpy.types.KeyMapItem') -> dict:
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
