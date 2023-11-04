# 每一项手势的快捷键
# 不需要去记录每一个快捷键的位置
# 只需要记录快捷键用到的数据和空间
# 每次开启插件的时候从数据里面当场新建一些快捷键并填入缓存数据
# 使用临时快捷键来修改每一个快捷键的位置
import traceback

import bpy
from bpy.types import KeyMapItem, PropertyGroup
from idprop.types import IDPropertyGroup

from .. import PropertyGetUtils
from ..key import get_temp_kmi
from ..public import PublicProperty
from ...ops import key


def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy', key_maps):
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
    row.prop(kmi, "active", text="", emboss=False)
    row.operator(key.OperatorSetKeyMaps.bl_idname)

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


class TempKey(PropertyGroup, PublicProperty):

    @property
    def temp_kmi_data(self):
        return dict(
            PropertyGetUtils.props_data(
                self.temp_kmi,
                exclude=('name', 'id', 'show_expanded', 'properties', 'idname')
            )
        )

    @property
    def temp_kmi(self) -> 'KeyMapItem':
        return get_temp_kmi(key.OperatorTempModifierKey.bl_idname, {'gesture': self.active_gesture.name})

    @property
    def keymap_hierarchy(self):
        from bl_keymap_utils import keymap_hierarchy
        return keymap_hierarchy.generate()

    @property
    def kmi_gesture(self):
        return self.temp_kmi.properties.gesture


class UpdateKey(TempKey):

    def _set_key(self, value):
        self['key'] = value

    def _get_key(self):
        default = {'type': 'NONE', 'value': 'PRESS'}
        if 'key' in self and dict(self['key']):
            default.update(
                {k: dict(v) if type(v) == IDPropertyGroup else v
                 for (k, v) in
                 dict(self['key']).items()}
            )
        return default

    def _get_keymap(self):
        return self['keymap'] if 'keymap' in self else ['Window', ]

    def _set_keymap(self, value):
        self['keymap'] = value
        self.update_key()

    key = property(fget=_get_key, fset=_set_key, doc='用来存快捷键的键位数据')

    keymap = property(fget=_get_keymap, fset=_set_keymap, doc='用来存快捷键可用的区域')

    def update_key(self):
        caller_name = traceback.extract_stack()[-2][2]
        print(self, "update_key 被 {} 调用".format(caller_name))

    @property
    def is_change_gesture(self) -> bool:
        return (self.kmi_gesture != self.active_gesture.name) or (not self.key)

    def from_temp_key_update_data(self):
        data = self.temp_kmi_data
        if self.key != data:
            self.key = data


class GestureKey(UpdateKey):
    def draw_key(self, layout):
        layout.operator(key.OperatorSetKeyMaps.bl_idname)
        layout.operator(key.OperatorTempModifierKey.bl_idname)

        # draw_kmi(layout, self.temp_kmi, self.keymap)
        layout.label(text=str(self.key))
        layout.label(text=str(self.keymap))
        # layout.label(text=self.temp_kmi)

        # self.from_temp_key_update_data()

    def load_key(self):
        # get_temp_kmi(key.OperatorTempModifierKey.bl_idname)
        ...

    def unload_key(self):
        ...

    @classmethod
    def start_load_key(cls):
        for g in cls._pref().gesture:
            g.load_key()

    @classmethod
    def stop_unload_key(cls):
        for g in cls._pref().gesture:
            g.unload_key()
