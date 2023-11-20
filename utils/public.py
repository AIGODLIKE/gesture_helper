from functools import cache
from os.path import dirname, basename, realpath

import bpy
from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator

from .public_cache import PublicCacheFunc

ADDON_NAME = basename(dirname(dirname(realpath(__file__))))


@cache
def get_pref():
    return bpy.context.preferences.addons[ADDON_NAME].preferences


class PublicProperty(PublicCacheFunc):

    @staticmethod
    def _pref():
        return get_pref()

    @property
    def pref(self):
        return self._pref()

    @property
    def draw_property(self):
        return self.pref.draw_property

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
                if element.radio:
                    return element


class PublicOperator(Operator):

    def invoke(self, context, event) -> set:
        PublicCacheFunc.gesture_cache_clear()
        PublicCacheFunc.element_cache_clear()
        return self.execute(context)


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

    def __check_duplicate_name__(self, context):
        names = list(self.__get_names)
        if len(names) != len(set(names)):
            for i in self.names_iteration:
                if self.__get_names.count(i.name) > 1:
                    self.cache_clear()
                    i.name = self.__generate_new_name__(self.__get_names, i.name)

    name: StringProperty(
        name='名称',
        description='不允许名称重复,如果名称重复则编号 e.g .001 .002 .999 支持重命名到999',
        update=__check_duplicate_name__
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
