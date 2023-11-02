from functools import cache
from os.path import dirname, basename, realpath

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, PropertyGroup

ADDON_NAME = basename(dirname(dirname(realpath(__file__))))


@cache
def get_pref():
    return bpy.context.preferences.addons[ADDON_NAME].preferences


class PublicCacheData:

    @staticmethod
    def _pref():
        return get_pref()

    @staticmethod
    def gesture_cache_clear():
        from .gesture import get_element_iteration, get_element_index
        get_element_iteration.cache_clear()
        get_element_index.cache_clear()

    @staticmethod
    def element_cache_clear():
        from .gesture.element import get_childes, get_parent_gesture, get_parent_element, get_element_index
        get_childes.cache_clear()
        get_parent_gesture.cache_clear()
        get_parent_element.cache_clear()
        get_element_index.cache_clear()

    @staticmethod
    def cache_clear():
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        get_pref.cache_clear()


class PublicProperty(PublicCacheData):

    @property
    def pref(self) -> 'GesturePreferences':
        return self._pref()

    @property
    def active_gesture(self):
        index = self.pref.index_gesture
        try:
            return self.pref.gesture[index]
        except IndexError:
            ...

    @property
    def active_element(self):
        try:
            if self.active_gesture:
                return self.active_gesture.element[self.active_gesture.index_element]
        except IndexError:
            ...


class PublicOperator(Operator, PublicProperty):

    def invoke(self, context, event):
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        return self.execute(context)


class PublicOnlyOneSelectedPropertyGroup(PropertyGroup, PublicProperty):
    """子级选中"""
    _items_iteration: []

    def _get_selected(self):
        if 'selected' not in self:
            self._set_selected(True)
        return self['selected']

    def _set_selected(self, _):
        for i in self._items_iteration:
            i['selected'] = i == self

    selected: BoolProperty(name='单选', get=_get_selected, set=_set_selected)


class PublicUniqueNamePropertyGroup(PropertyGroup, PublicProperty):
    """不重复名称"""
    _items_iteration: []

    @staticmethod
    def __generate_new_name__(names, new_name):
        # 检查新名称是否已存在,
        if new_name in names:
            base_name = new_name
            count = 1
            while new_name in names:
                new_name = f"{base_name}.{count:03}"
                count += 1
        return new_name

    @property
    def __get_names(self):
        self.__handler_duplicate_name__()
        return list(map(lambda s: s.name, self._items_iteration))

    def _get_name(self):
        if 'name' not in self:
            self['name'] = 'Gesture'
            self.name = 'Gesture'
        return self['name']

    def _set_name(self, value):
        old_name = self['name'] if 'name' in self else None
        new_name = self.__generate_new_name__(self.__get_names, value)
        self['name'] = new_name
        self.__check_duplicate_name__()

        func = getattr(self, 'update_name', lambda i, j: i)
        if func:
            func(new_name, old_name)

    def __check_duplicate_name__(self):
        items = list(self._items_iteration)
        if len(items) != len(set(items)):
            for i in list(self._items_iteration):
                i.name = i.name

    name: StringProperty(
        name='名称',
        description='不允许名称重复,如果名称重复则编号 e.g .001 .002 .999 支持重命名到999',
        get=_get_name,
        set=_set_name
    )
