import bpy
from bpy.app.translations import contexts as i18n_contexts
from functools import cache
import abc
from bpy.props import StringProperty, IntProperty

from .log import log

exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项

_base_data = {'name': 'name',
              'description': 'description',
              'options': 'options',
              'override': 'override',
              #   'tags': 'tags', ERROR
              }
_generic_data = {**_base_data,
                 'default': 'default',
                 'subtype': 'subtype',
                 }

_math_property = {**_generic_data,
                  'hard_min': 'min',  # change
                  'hard_max': 'max',  # change
                  'soft_min': 'soft_min',
                  'soft_max': 'soft_max',
                  'step': 'step',
                  }

_float_property = {**_math_property,
                   'precision': 'precision',
                   'unit': 'unit',
                   }

property_data = {  # 属性参数
    'EnumProperty': {'items': 'items',
                     **_generic_data},

    'StringProperty': {**_generic_data},

    'PointerProperty': {'type': 'type',
                        **_base_data},
    'CollectionProperty': {'type': 'type',
                           **_base_data},

    'BoolProperty': {**_generic_data},
    'BoolVectorProperty': {'size': 'size',
                           **_generic_data},

    'FloatProperty': _float_property,
    'FloatVectorProperty': {'size': 'size',
                            **_float_property},

    'IntProperty': _math_property,
    'IntVectorProperty': {'size': 'size', **_math_property},
}


def from_bl_rna_get_bl_property_data(parent_prop: object, property_name: str, msgctxt=None, fill_copy=False) -> dict:
    """从bl_rna 获取blender属性的数据
    BoolProperty(data)

    Args:
        parent_prop (object): bl数据
        property_name (str): 数据名称
        msgctxt (_type_, optional): 翻译上下文. Defaults to None.
        fill_copy (bool, optional): 完全复制所有属性. Defaults to False.

    Returns:
        dict: 反回bl属性的数据

    """

    bl_rna = getattr(parent_prop, 'bl_rna', None)
    if not bl_rna:
        print(Exception(f'{parent_prop} no bl_rna'))
        return dict()

    ret_data = {}
    pro = bl_rna.properties[property_name]
    typ = pro.type
    property_fill_name = type(pro.type_recast()).__name__

    def get_t(text, msg):
        import bpy
        return bpy.app.translations.pgettext_iface(
            text, msgctxt=msg)

    if fill_copy:
        # 获取输入属性的所有参数
        for i in property_data[property_fill_name]:
            prop = getattr(pro, i, None)
            if prop is not None:
                index = property_data[property_fill_name][i]
                ret_data[index] = prop

    if typ == 'ENUM':
        ret_data['items'] = [(i.identifier,
                              get_t(i.name, msgctxt) if msgctxt else i.name,
                              i.description,
                              i.icon,
                              i.value)
                             for i in pro.enum_items]
    return ret_data


def set_ctext_enum():
    """将翻译上下文enum的名称改为正常并且去掉__doc__
    """
    data = []
    for item in dir(i18n_contexts):
        prop = getattr(i18n_contexts, item, None)
        if prop and type(prop) == str:
            if item in ('__doc__',):
                continue
            if 'id_' == item[:3]:
                add = item[3:].replace('_', ' ')
            else:
                add = item.replace('_', ' ')
            data.append((item, add.title(), ''))
    return data


@cache
def get_pref():
    from .property import ADDON_NAME
    return bpy.context.preferences.addons[ADDON_NAME].preferences


class _Miss:

    @property
    def _items(self):
        """反回父项"""

    @property
    def _keys(self):
        """反回集合项"""
        return self._items.keys()


class PublicClass:

    @staticmethod
    def cache_clear():
        get_pref.cache_clear()

    @staticmethod
    def pref_():
        return get_pref()

    @property
    def pref(self) -> 'GestureAddonPreferences':
        return self.pref_()

    @property
    def element_items(self):
        return self.pref.gesture_element_items

    @property
    def active_element(self):
        index = self.pref.active_index
        items_len = len(self.element_items)
        if not items_len:
            return
        elif index >= items_len:
            index = items_len - 1
        return self.element_items[index]

    @property
    def active_ui_element(self):
        if self.active_element:
            act = self.active_element
            return act.ui_element_items[act.active_index]


class PublicName(_Miss):
    @staticmethod
    def _get_suffix(string):
        sp = string.split('.')
        try:
            return int(sp[-1])
        except ValueError as e:
            log.info(f'_get_suffix change name to {string, e.args}')
            return -1

    @classmethod
    def _suffix_is_number(cls, string: str) -> bool:
        _i = cls._get_suffix(string)
        if _i == -1:
            return False
        return True

    def get_name(self):
        if 'name' not in self:
            self.set_name('New Element')
        return self['name']

    def chick_name(self):
        for key in self._keys:
            self._items[key].set_name(key)

    def _get_effective_name(self, value):

        def _get_number(n):
            if n < 999:
                return f'{n}'.rjust(3, '0')
            return f'1'.rjust(3, '0')

        if value in self._keys:
            if self._suffix_is_number(value):
                log.debug(f'_suffix_is_number {self._get_suffix(value)}')
                number = _get_number(self._get_suffix(value) + 1)
                sp = value.split('.')
                sp[-1] = number
                value = '.'.join(sp)
            else:
                value += '.001'
            return self._get_effective_name(value)
        return value

    def set_name(self, value):
        keys = self._keys
        if 'name' in self and value == self['name'] and keys.count(value) < 2:
            return
        name = self._get_effective_name(value)
        self['name'] = name

        if (len(keys) - len(set(keys))) >= 1:  # 有重复的名称
            self.chick_name()
        if getattr(self, 'change_name', False):
            self.change_name(name)

    def update_name(self, context):
        ...

    name: StringProperty(
        name='name',
        get=get_name,
        set=set_name,
        update=update_name,
    )


class PublicIndex(_Miss):
    def _get_active_index(self):
        if 'active_index' not in self:
            return 0
        index = self['active_index']
        items_len = len(self._items)
        return items_len - 1 if index >= items_len else index

    def _set_active_index(self, value):
        self['active_index'] = value

    active_index: IntProperty(
        name='活动项索引',
        get=_get_active_index,
        set=_set_active_index,
    )
