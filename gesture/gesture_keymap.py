"""
每一项手势的快捷键
不需要去记录每一个快捷键的位置
只需要记录快捷键用到的数据和空间
每次开启插件的时候从数据里面当场新建一些快捷键并填入缓存数据
使用临时快捷键来修改每一个快捷键的位置
"""

import json
import traceback

import bpy
from bpy.app.translations import pgettext
from bpy.props import StringProperty
from idprop.types import IDPropertyGroup

from ..utils import PropertyGetUtils, PropertySetUtils
from ..utils.public import get_debug
from ..utils.public_cache import cache_update_lock
from ..utils.public_key import get_temp_kmi, get_temp_keymap, add_addon_kmi, draw_kmi

default_key = {'type': 'NONE', 'value': 'PRESS'}


class KeymapProperty:
    __key_data__ = {}  # {self:(keymap:kmi)}

    __key__ = 'key'
    __keymaps__ = 'keymaps'

    def set_key(self, value) -> None:
        self[self.__key__] = value
        self.key_update()

    def get_key(self) -> dict:
        default = default_key.copy()
        key = self.__key__
        if key in self and dict(self[key]):
            default.update(
                {k: dict(value) if value is IDPropertyGroup else value
                 for (k, value) in
                 dict(self[key]).items()}
            )
        return default

    def get_keymap(self) -> list:
        key = self.__keymaps__
        return self[key] if key in self else ['Window', ]

    def set_keymap(self, value) -> None:
        self[self.__keymaps__] = value
        self.key_update()

    key = property(fget=get_key, fset=set_key, doc='用来存快捷键的键位数据')
    keymaps = property(fget=get_keymap, fset=set_keymap, doc='用来存快捷键可用的区域')

    key_string: StringProperty(get=lambda self: json.dumps(self.get_key()),
                               set=lambda self, value: self.set_key(json.loads(value)))
    keymaps_string: StringProperty(get=lambda self: json.dumps(self.get_keymap()),
                                   set=lambda self, value: self.set_keymap(json.loads(value)))


class GestureKeymap(KeymapProperty):

    @property
    def temp_kmi_data(self) -> dict:
        return PropertyGetUtils.kmi_props(self.temp_kmi)

    @property
    def temp_kmi(self) -> 'bpy.types.KeyMapItem':
        from ..ops import set_key
        return get_temp_kmi(set_key.OperatorTempModifierKey.bl_idname, {'gesture': self.name})

    @property
    def add_kmi_data(self) -> dict:
        from ..ops import gesture
        return {'idname': gesture.GestureOperator.bl_idname, **self.key}

    def from_temp_key_update_data(self) -> None:
        data = self.temp_kmi_data
        if self.key != data:
            print(f"from_temp_key_update_data\n{data}\n{self.key}")
            self.key = data

    def to_temp_kmi(self) -> None:
        key = ",".join(list(f"{k.title()}={v}" for k, v in self.key.items()))
        print(f'Gesture -> Kmi {self.name} (%s)' % key)
        PropertySetUtils.set_property_data(self.temp_kmi, self.key)

    def draw_key(self, layout) -> None:
        layout.context_pointer_set('keymap', get_temp_keymap())

        draw_kmi(layout, self.temp_kmi, self.keymaps)
        if get_debug():
            layout.label(text=str(self.key))
            layout.label(text=str(self.keymaps))
            layout.label(text=str(self.temp_kmi.id))
            layout.label(text=str(self.temp_kmi))
            layout.label(text=str(self.temp_kmi_data))
        self.from_temp_key_update_data()

    def key_load(self) -> None:
        if self.is_enable:
            if self in GestureKeymap.__key_data__:  # 还没注销
                self.key_unload()
            data = GestureKeymap.__key_data__[self] = []
            if get_debug('key'):
                print('Add Kmi Data', self.name, self.add_kmi_data)
            for keymap in self.keymaps:
                data.append(add_addon_kmi(keymap, self.add_kmi_data, {'gesture': self.name}))

    def key_unload(self) -> None:
        if self in GestureKeymap.__key_data__:  # 如果禁用了会出现没有快捷键的情况
            for keymap, kmi in GestureKeymap.__key_data__.pop(self):
                if kmi in keymap.keymap_items.values():
                    keymap.keymap_items.remove(kmi)

    @cache_update_lock
    def key_update(self) -> None:
        # 在keymap被改时更新
        # 在key被改时更新
        caller_name = traceback.extract_stack()[-2][2]
        self.key_unload()
        self.key_load()
        if get_debug('key'):
            print("Key Update 被 {} 调用".format(caller_name), self)

    @classmethod
    def key_init(cls) -> None:
        """加载所有快捷键"""
        from ..utils.public import get_pref
        for g in get_pref().gesture:
            g.key_load()

    @classmethod
    def key_remove(cls) -> None:
        """删除所有快捷键"""

        for i in list(GestureKeymap.__key_data__.keys()):
            i.key_unload()

    @classmethod
    def key_restart(cls) -> None:
        cls.key_remove()
        cls.key_init()

    def restore_key(self):
        self.key = default_key
        kmi = self.temp_kmi
        kmi.map_type = 'KEYBOARD'
        kmi.shift = False
        kmi.ctrl = False
        kmi.alt = False
        self.to_temp_kmi()

    @property
    def __key_str__(self) -> str:
        """反回快捷键显示的字符"""
        from ..src.translate import __keymap_translate__
        keymap = self.key
        if keymap:
            items = [
                k.title()[0] if isinstance(v, int) else __keymap_translate__(v)
                for k, v in keymap.items()
                if k == 'type' or (k in ('ctrl', 'shift', 'alt') and v == 1)
            ]
            if bpy.context.preferences.view.use_translate_interface:
                return "".join(items)
            else:
                return " ".join(items)
        else:
            return pgettext("Not key")
