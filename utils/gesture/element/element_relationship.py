from functools import cache

from bpy.props import BoolProperty, StringProperty

from ...public import (get_pref,
                       PublicSortAndRemovePropertyGroup, PublicUniqueNamePropertyGroup)


@cache
def get_parent_element(element):
    for e in element.parent_gesture.element_iteration:
        if element in e.element.values():
            return e


@cache
def get_element_index(element) -> int:
    try:
        return element.collection.values().index(element)
    except ValueError:
        ...


class Relationship:
    @property
    def parent_element(self):
        from ...public_cache import PublicCache
        return PublicCache.__element_parent_element_cache__[self]

    @property
    def parent_gesture(self):
        from ...public_cache import PublicCache
        return PublicCache.__element_parent_gesture_cache__[self]

    @property
    def collection_iteration(self) -> list:
        from ...public_cache import PublicCache
        items = []
        for element in self.parent_gesture.element:
            items.extend(PublicCache.__element_child_iteration__[element])
        return items

    @property
    def collection(self):
        pe = self.parent_element
        if pe:
            return pe.element
        else:
            return self.parent_gesture.element

    @property
    def element_iteration(self):
        from ...public_cache import PublicCache
        return PublicCache.__gesture_element_iteration__[self.parent_gesture]


class RadioSelect:

    def _update_radio(self, context):

        for i in self.radio_iteration:
            print(i == self, i, self)
            i['radio'] = i == self
        f = getattr(self, 'selected_update')
        if f:
            f(context)
        print('self.radio_iteration', self.radio_iteration)

    radio: BoolProperty(name='单选',
                        update=_update_radio
                        )

    @property
    def radio_iteration(self):
        return self.parent_gesture.element_iteration


class ElementRelationship(
    PublicUniqueNamePropertyGroup,
    RadioSelect,
    PublicSortAndRemovePropertyGroup,
    Relationship):

    def _get_index(self) -> int:
        return get_element_index(self)

    def _set_index(self, value):
        if self.is_root:
            self.parent_gesture['index_element'] = self.index
        else:
            self.parent_element['index_element'] = self.index

    index = property(
        fget=_get_index,
        fset=_set_index,
        doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def is_root(self):
        return self in self.parent_gesture.element.values()

    def selected_update(self, context):
        """
        在选择其它子项的时候自动将活动索引切换
        @rtype: object
        """
        if self.is_root:
            for (index, element) in enumerate(self.parent_gesture.element):
                if self in element.collection_iteration:
                    self.parent_gesture['index_element'] = self.index

    @property
    def names_iteration(self):
        return self.parent_gesture.element_iteration

    def remove_before(self):
        for e in self.element:
            e.remove()
        return
