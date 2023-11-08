from functools import cache
from os.path import dirname, basename, realpath

import bpy
from bpy.props import BoolProperty, StringProperty, CollectionProperty
from bpy.types import Operator

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
        print('gesture_cache_clear')
        from .gesture import gesture_relationship
        gesture_relationship.get_element_iteration.cache_clear()
        gesture_relationship.get_gesture_index.cache_clear()

    @staticmethod
    def element_cache_clear():
        print('element_cache_clear')
        from .gesture.element import element_relationship
        element_relationship.get_childes.cache_clear()
        element_relationship.get_parent_gesture.cache_clear()
        element_relationship.get_parent_element.cache_clear()
        element_relationship.get_element_index.cache_clear()

    @staticmethod
    def poll_cache_clear():
        # TODO
        ...

    @staticmethod
    def cache_clear():
        print('cache_clear')
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        PublicCacheData.poll_cache_clear()
        get_pref.cache_clear()


class PublicProperty(PublicCacheData):

    @property
    def pref(self):
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
        act_ges = self.active_gesture
        if act_ges and len(act_ges.element):
            for element in act_ges.element_iteration:
                if element.selected:
                    return element


class PublicOperator(Operator):

    def invoke(self, context, event) -> set:
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        return self.execute(context)


class PublicOnlyOneSelectedPropertyGroup:
    """子级选中"""
    selected_iteration: CollectionProperty

    def _get_selected(self):
        if 'selected' not in self:
            self._set_selected(True)
        return bool(self['selected'])

    def _set_selected(self, _):
        for i in self.selected_iteration:
            i['selected'] = i == self

    def _update_selected(self, context):
        f = getattr(self, 'selected_update')
        if f:
            f(context)

    selected: BoolProperty(name='单选', get=_get_selected, set=_set_selected, update=_update_selected)


class PublicUniqueNamePropertyGroup:
    """不重复名称"""
    names_iteration: list

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
        return list(map(lambda s: s.name, self.names_iteration))

    def _get_name(self):
        if 'name' not in self:
            self['name'] = 'Gesture'
            self.name = 'Gesture'
        return self['name']

    def _set_name(self, value):
        old_name = self['name'] if 'name' in self else None

        self['name'] = value  # 预先注入名称测试有无多项一样的
        if self.__get_names.count(value) > 1:  # 避免一直增量
            new_name = self.__generate_new_name__(self.__get_names, value)
        else:
            new_name = value
        self['name'] = new_name

        self.__check_duplicate_name__()

        getattr(self, 'update_name', lambda i, j: i)(new_name, old_name)

    def __check_duplicate_name__(self):
        names = list(self.__get_names)
        if len(names) != len(set(names)):
            for i in self.names_iteration:
                i['name'] = self.__generate_new_name__(self.__get_names, i.name)

    name: StringProperty(
        name='名称',
        description='不允许名称重复,如果名称重复则编号 e.g .001 .002 .999 支持重命名到999',
        get=_get_name,
        set=_set_name
    )


class PublicSortAndRemovePropertyGroup:
    index: int
    collection: CollectionProperty

    def _get_index(self):
        return 0

    def _set_index(self, value):
        ...

    index = property(fget=_get_index, fset=_set_index, doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def is_last(self) -> bool:
        """
        反回此手势 是否为最后一个的布尔值
        用于移动手势位置
        @rtype: object
        """
        return self == self.collection[-1]

    @property
    def is_first(self) -> bool:
        """
        反回此手势 是否为第一个的布尔值
        用于移动手势位置
        @return:
        """
        return self == self.collection[0]

    def sort(self, is_next):
        col = self.collection
        gl = len(col)
        if is_next:
            if self.is_last:
                col.move(gl - 1, 0)
                self.index = 0
            else:
                col.move(self.index, self.index + 1)
                self.index = self.index + 1
        else:
            if self.is_first:
                col.move(self.index, gl - 1)
                self.index = gl - 1
            else:
                col.move(self.index - 1, self.index)
                self.index = self.index - 1

    def remove(self):
        getattr(self, 'remove_before', lambda: ...)()  # TODO 切片方法 装饰器
        self.collection.remove(self.index)
        getattr(self, 'remove_after', lambda: ...)()
