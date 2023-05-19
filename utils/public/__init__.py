import ast
from functools import cache

import bpy
from bpy.types import AddonPreferences, Operator, UILayout
from mathutils import Euler, Matrix, Vector

from .public_data import PublicData
from .public_func import PublicMethod


class PublicProperty:
    @staticmethod
    @cache
    def pref_() -> 'AddonPreferences':
        return bpy.context.preferences.addons[PublicData.G_ADDON_NAME].preferences

    @property
    def pref(self) -> 'AddonPreferences':
        return PublicProperty.pref_()

    @property
    def systems(self):
        return self.pref.systems

    @property
    def active_system(self):
        index = self.pref.active_index
        try:
            return self.systems[index]
        except IndexError:
            ...

    @property
    def active_ui_element(self):
        """
        :return: UiElementItem
        """
        if self.active_system:
            try:
                return self.active_system.selected_children_element[-1]
            except IndexError:
                ...

    @property
    def ui_prop(self):
        return self.pref.ui_property


class CacheHandler(PublicProperty,
                   PublicMethod):
    @classmethod
    def cache_clear(cls):
        cls.pref_.cache_clear()

    @staticmethod
    def tag_redraw(context):
        if context.area:
            context.area.tag_redraw()


class PublicOperator(
    CacheHandler,
    Operator
):
    @staticmethod
    def ops_id_name(string):
        return 'emm_operator.' + string


class TempKey:
    @property
    def keyconfig(self):
        return bpy.context.window_manager.keyconfigs.active

    @property
    def temp_keymaps(self):
        if 'TEMP' not in self.keyconfig.keymaps:
            self.keyconfig.keymaps.new('TEMP')
        return self.keyconfig.keymaps['TEMP']

    def get_temp_kmi(self, idname):
        key = idname
        keymap_items = self.temp_keymaps.keymap_items
        if key not in keymap_items:
            return keymap_items.new(key, 'NONE', 'PRESS')
        return keymap_items[key]

    @staticmethod
    def _get_operator_property(string: str) -> dict:

        """将输入的字符串操作符属性转成字典
        用于传入操作符执行操作符用

        Args:
            string (str): _description_
        Returns:
            dict: _description_
        """
        property_dict = {}
        for prop in string[1:-1].split(', '):  # ['animation=True', ' use_viewport=True']
            try:
                par, value = prop.split('=')
                property_dict[par] = ast.literal_eval(value)
            except ValueError as v:
                print(v.args)
        return property_dict

    @staticmethod
    def from_kmi_get_operator_properties(kmi: 'bpy.types.KeyMapItem') -> str:
        """获取临时kmi操作符的属性
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
        return str(dictionary)

    @staticmethod
    def _for_set_prop(prop, pro, pr):
        for index, j in enumerate(pr):
            try:
                getattr(prop, pro)[index] = j
            except Exception as e:
                print(e.args)

    def set_operator_property_to(self, property_str, properties: 'bpy.types.KeyMapItem.properties') -> None:
        """注入operator property
        在绘制项时需要使用此方法
        set operator property
        self.operator_property:

        Args:
            properties (bpy.types.KeyMapItem.properties): _description_
            :param properties:
            :param property_str:
        """
        props = ast.literal_eval(property_str)
        for pro in props:
            pr = props[pro]
            if hasattr(properties, pro):
                if type(pr) == tuple:
                    # 阵列参数
                    self._for_set_prop(properties, pro, pr)
                else:
                    try:
                        setattr(properties, pro, props[pro])
                    except Exception as e:
                        print(e.args)

    def from_operator_info_get_property(self, string):
        ...


class PublicClass(
    CacheHandler,
):
    layout: UILayout


def register_module_factory(module):
    is_debug = False

    def reg():
        for mod in module:
            if is_debug:
                print('register ', mod)
            mod.register()

    def un_reg():
        for mod in reversed(module):
            if is_debug:
                print('unregister ', mod)
            mod.unregister()

    return reg, un_reg
