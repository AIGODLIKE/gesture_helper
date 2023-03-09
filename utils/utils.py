from functools import cache

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.types import Operator

from .log import log
from .property import SKIP_DEFAULT


@cache
def get_pref():
    from .property import ADDON_NAME
    return bpy.context.preferences.addons[ADDON_NAME].preferences


@cache
def get_debug():
    import os
    return os.getlogin() in ('EM1', 'EMM', 'Emm')


class _Miss:

    @property
    def _items(self):
        """反回父项"""

    @property
    def _keys(self):
        """反回集合项"""
        return self._items.keys()

    @property
    def _index(self):
        ...


class PublicClass:
    _parent_element_key = 'parent_element_key'  # 父元素key
    _parent_ui_key = 'parent_ui_emm'  # 父ui元素key
    _child_ui_key = 'child_ui_key_emm'  # 子ui元素列表key
    _children_ui_element_not_parent_key = 'children_ui_element_not_parent_key'  # 没有子级元素的子项列表key,放在父元素里面存着
    _not_copy_list = (
        # _parent_element_key,
        # _parent_ui_key,
        'is_update',
        _child_ui_key,
        _children_ui_element_not_parent_key,
    )
    is_update: BoolProperty(default=True)

    @staticmethod
    def cache_clear():
        get_pref.cache_clear()
        get_debug.cache_clear()

    @staticmethod
    def pref_():
        return get_pref()

    @property
    def pref(self) -> 'GestureAddonPreferences':
        return self.pref_()

    @property
    def element_items(self):
        return self.pref.gesture_element_collection_group

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
        act = self.active_element
        if act and act.ui_items_collection_group:
            return act.ui_items_collection_group[act.active_index]

    @property
    def is_debug(self):
        return get_debug() and self.pref.is_debug

    @staticmethod
    def tag_redraw(context):
        if context.area:
            context.area.tag_redraw()


class PublicName(_Miss):
    @staticmethod
    def _get_suffix(string):
        sp = string.split('.')
        try:
            return int(sp[-1])
        except ValueError as e:
            return -1

    @classmethod
    def _suffix_is_number(cls, string: str) -> bool:
        _i = cls._get_suffix(string)
        if _i == -1 or len(string) < 3:
            return False
        return True

    @property
    def _not_update_name(self):
        return 'name' not in self

    def _get_name(self):
        if self._not_update_name:
            return f'not update name {self}'
        elif 'name' not in self:
            self._set_name('New Name')

        return self['name']

    def chick_name(self):
        # for key in self._keys:
        #     self._items[key]._set_name(key)
        ...

    def _get_effective_name(self, value):

        def _get_number(n):
            if n < 999:
                return f'{n}'.rjust(3, '0')
            return f'1'.rjust(3, '0')

        if value in self._keys:
            if self._suffix_is_number(value):
                number = _get_number(self._get_suffix(value) + 1)
                sp = value.split('.')
                sp[-1] = number
                value = '.'.join(sp)
            else:
                value += '.001'
            return self._get_effective_name(value)
        return value

    def _set_name(self, value):
        keys = self._keys
        not_update = ('name' in self and value == self['name'] and keys.count(value) < 2)
        if not_update or not value:
            log.debug(f'not_set name\t"{self["name"]}" value to\t"{value}"')
            return
        name = self._get_effective_name(value)

        log.debug(f'set name {name}')
        old_name = self['name'] if 'name' in name else None

        self['name'] = name

        if getattr(self, 'change_name', False):
            self.change_name(old_name, name)
        if (len(keys) - len(set(keys))) >= 1:  # 有重复的名称
            self.chick_name()

    def change_name(self, old_name, new_name):
        ...

    def set_name(self, name):
        self['name'] = self.name = name

    def _update_name(self, context):
        ...

    name: StringProperty(
        name='name',
        get=_get_name,
        set=_set_name,
        update=_update_name,
    )


class PublicMove(_Miss):

    def move(self, is_next=True):
        ...

    @staticmethod
    def move_collection_element(collection_prop, active_prop, active_name: str = 'active_index', is_next=True) -> None:
        prop_len = len(collection_prop)
        index = getattr(active_prop, active_name, 0)
        if is_next:
            if prop_len - 1 <= index:
                collection_prop.move(index, 0)
                act_ind = 0
            else:
                collection_prop.move(index, index + 1)
                act_ind = index + 1
        else:
            if 0 >= index:
                collection_prop.move(index, prop_len - 1)
                act_ind = prop_len - 1
            else:
                collection_prop.move(index, index - 1)
                act_ind = index - 1
        setattr(active_prop, active_name, act_ind)


class PublicIndex(_Miss):

    @property
    def _index_items(self):
        ...

    def _get_active_index(self):
        if 'active_index' not in self:
            return 0
        index = self['active_index']
        items_len = len(self._index_items)
        return items_len - 1 if index >= items_len else index

    def _set_active_index(self, value):
        self['active_index'] = value

    active_index: IntProperty(
        name='活动项索引',
        get=_get_active_index,
        set=_set_active_index,
    )


class PublicPopup(Operator):
    is_popup_menu: BoolProperty(name='弹出菜单',
                                description='''是否为弹出菜单,如果为True则弹出菜单,''',
                                default=True,
                                **SKIP_DEFAULT,
                                )
    title: str

    def draw_menu(self, menu, context):
        menu.layout.label(text='label')

    def invoke(self, context, event):
        if self.is_popup_menu:
            context.window_manager.popup_menu(
                self.draw_menu, title=getattr(self, 'title', self.bl_label))
            return {'FINISHED'}
        return self.execute(context)
