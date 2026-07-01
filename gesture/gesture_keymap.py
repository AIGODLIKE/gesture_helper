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

from ..debug import TMP_KMI_SYNC_DEBUG
from ..utils.property import set_property, get_kmi_property
from ..utils.public import get_debug
from ..utils.public_cache import cache_update_lock
from .addon_keymap import AddonKeymapRegistry, add_addon_kmi, clear_orphan_gesture_kmis
from .temp_keymap import draw_temp_keymap_item, get_temp_kmi

default_key = {'type': 'RIGHTMOUSE', 'value': 'PRESS'}


class KeymapProperty:
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
        return self[key] if key in self else ['Window', "3D View", "Object Mode", "Mesh"]

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
        return get_kmi_property(self.temp_kmi)

    @property
    def temp_kmi(self) -> bpy.types.KeyMapItem:
        from ..ops import set_key
        return get_temp_kmi(set_key.OperatorTempModifierKey.bl_idname, {'gesture': self.name})

    @property
    def add_kmi_data(self) -> dict:
        from ..ops import gesture
        return {'idname': gesture.GestureOperator.bl_idname, **self.key}

    @cache_update_lock
    def from_temp_key_update_data(self) -> None:
        data = self.temp_kmi_data
        if self.key != data:
            if TMP_KMI_SYNC_DEBUG:
                print(f"from_temp_key_update_data")
                print(self.key)
                print(data)
            self.key = data
            self.key_restart()

    def to_temp_kmi(self) -> None:
        key = ",".join(list(f"{k.title()}={v}" for k, v in self.key.items()))
        print(f'Gesture -> Temp kmi {self.name} (%s)' % key)
        set_property(self.temp_kmi, self.key)

    def draw_key(self, layout) -> None:
        draw_temp_keymap_item(layout, self.temp_kmi, self.keymaps)
        if get_debug():
            layout.label(text=str(self.key))
            layout.label(text=str(self.keymaps))
            layout.label(text=str(self.temp_kmi.id))
            layout.label(text=str(self.temp_kmi))
            layout.label(text=str(self.temp_kmi_data))
        self.from_temp_key_update_data()

    def key_load(self) -> None:
        if not self.is_enable:
            return
        kmi_data = dict(self.add_kmi_data)
        properties = {"gesture": self.name}
        if get_debug("key"):
            content = {k: v for k, v in kmi_data.items() if k in ("type", "value")}
            print(f"Add Kmi\t{content} to {self.keymaps}", flush=True)
        for keymap_name in self.keymaps:
            add_addon_kmi(keymap_name, kmi_data, properties)

    @cache_update_lock
    def key_update(self) -> None:
        self.key_restart()
        if get_debug('key'):
            caller_name = traceback.extract_stack()[-2][2]
            print("Key Update 被 {} 调用".format(caller_name), self)

    @classmethod
    def key_all_load(cls) -> None:
        """加载所有快捷键"""
        from ..utils.public import get_pref
        for g in get_pref().gesture:
            g.key_load()

    @classmethod
    def key_all_unload(cls) -> None:
        """卸载所有快捷键（仅使用注册列表）"""
        AddonKeymapRegistry.clear()

    @classmethod
    def key_clear_legacy(cls) -> int:
        """清理快捷键，包含遗留项扫描（register/unregister 时调用）"""
        cls.key_all_unload()
        clear_count = clear_orphan_gesture_kmis()
        if get_debug('key'):
            print("Gesture Clear Legacy Keymap count", clear_count, flush=True)
        return clear_count

    @classmethod
    def key_restart(cls) -> None:
        """重置键位（仅通过注册列表卸载后重新加载）"""
        cls.key_all_unload()
        cls.key_all_load()
        if get_debug('key'):
            print("Gesture Key Restart", AddonKeymapRegistry.entry_count())
            import traceback
            for i in traceback.extract_stack():
                print(i)

    def restore_key(self):
        """重置快捷键"""
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
