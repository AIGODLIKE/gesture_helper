from functools import cache

import bpy

from .gesture_public import GesturePublic
from ..public import get_pref


@cache
def get_element_iteration(gesture: 'bpy.types.PropertyGroup'):
    items = []

    def get_element(j):
        for f in j.element:
            get_element(f)
        items.append(j)

    for i in gesture:
        get_element(i)
    return items


@cache
def get_gesture_index(gesture) -> int:
    return gesture.pref.gesture.values().index(gesture)


class GestureRelationship(GesturePublic):

    @property
    def element_iteration(self):
        return get_element_iteration(self.element)

    @property
    def collection_iteration(self) -> list:
        return get_pref().gesture.values()

    @property
    def names_iteration(self):
        return self.collection_iteration

    def _get_index_(self) -> int:
        return get_gesture_index(self)

    def _set_index_(self, value: int) -> None:
        get_pref().index_gesture = value

    index = property(fget=_get_index_, fset=_set_index_, doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def collection(self):
        return get_pref().gesture

    @property
    def is_enable(self) -> bool:
        """
        @rtype: bool
        """
        return get_pref().enabled and self.enabled

    def remove_before(self):
        if self.is_last and self.index != 0:  # 被删除项是最后一个
            self.index = self.index - 1  # 索引-1,保持始终有一个所选项
