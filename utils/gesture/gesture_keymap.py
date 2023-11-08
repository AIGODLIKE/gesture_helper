# 每一项手势的快捷键
# 不需要去记录每一个快捷键的位置
# 只需要记录快捷键用到的数据和空间
# 每次开启插件的时候从数据里面当场新建一些快捷键并填入缓存数据
# 使用临时快捷键来修改每一个快捷键的位置
import traceback

import bpy
from idprop.types import IDPropertyGroup

from .gesture_public import GesturePublic
from .. import PropertyGetUtils
from ..public_key import get_temp_kmi, get_temp_keymap, add_addon_kmi, draw_kmi


class GestureKeymap(GesturePublic):
    __key_data__ = {}  # {self:(keymap:kmi)}

    def _set_key(self, value) -> None:
        self['key'] = value
        self.key_update()

    def _get_key(self) -> dict:
        default = {'type': 'NONE', 'value': 'PRESS'}
        if 'key' in self and dict(self['key']):
            default.update(
                {k: dict(value) if type(value) == IDPropertyGroup else value
                 for (k, value) in
                 dict(self['key']).items()}
            )
        return default

    def _get_keymap(self) -> list:
        return self['keymap'] if 'keymap' in self else ['Window', ]

    def _set_keymap(self, value) -> None:
        self['keymap'] = value
        self.key_update()

    key = property(fget=_get_key, fset=_set_key, doc='用来存快捷键的键位数据')
    keymaps = property(fget=_get_keymap, fset=_set_keymap, doc='用来存快捷键可用的区域')

    @property
    def temp_kmi_data(self) -> dict:
        return dict(
            PropertyGetUtils.props_data(
                self.temp_kmi,
                exclude=(
                    'name', 'id', 'show_expanded', 'properties', 'idname', 'map_type', 'active', 'propvalue',
                    'shift_ui', 'ctrl_ui', 'alt_ui', 'oskey_ui'
                )
            )
        )

    @property
    def temp_kmi(self) -> 'bpy.types.KeyMapItem':
        from ...ops import set_key
        return get_temp_kmi(set_key.OperatorTempModifierKey.bl_idname, {'gesture': self.name})

    @property
    def add_kmi_data(self) -> dict:
        from ...ops import gesture
        return {'idname': gesture.GestureOperator.bl_idname, **self.temp_kmi_data}

    def from_temp_key_update_data(self) -> None:
        data = self.temp_kmi_data
        if self.key != data:
            self.key = data

    def draw_key(self, layout) -> None:
        from ...ops import set_key
        layout.context_pointer_set('keymap', get_temp_keymap())

        layout.operator(set_key.OperatorSetKeyMaps.bl_idname)
        layout.operator(set_key.OperatorTempModifierKey.bl_idname)

        draw_kmi(layout, self.temp_kmi, self.keymaps)
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
            for keymap in self.keymaps:
                data.append(add_addon_kmi(keymap, self.add_kmi_data, {'gesture': self.name}))

    def key_unload(self) -> None:
        if self in GestureKeymap.__key_data__:  # 如果被禁用了会出现没有快捷键的情况
            for keymap, kmi in GestureKeymap.__key_data__[self]:
                keymap.keymap_items.remove(kmi)
            GestureKeymap.__key_data__.pop(self)

    def key_update(self) -> None:
        # 在keymap被改时更新
        # 在key被改时更新
        caller_name = traceback.extract_stack()[-2][2]
        print("key_update 被 {} 调用".format(caller_name), self)
        self.key_unload()
        self.key_load()

    @classmethod
    def key_init(cls) -> None:
        from ..public import get_pref
        for g in get_pref().gesture:
            g.key_load()

    @classmethod
    def key_remove(cls) -> None:
        from ..public import get_pref
        for g in get_pref().gesture:
            g.key_unload()

    @classmethod
    def key_restart(cls) -> None:
        cls.key_remove()
        cls.key_init()
