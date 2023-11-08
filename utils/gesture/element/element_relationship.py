from functools import cache

from ...public import (get_pref,
                       PublicUniqueNamePropertyGroup,
                       PublicSortAndRemovePropertyGroup,
                       PublicOnlyOneSelectedPropertyGroup)


@cache
def get_childes(element):
    childes = element.element.values()
    if len(childes):
        for child in childes:
            childes.extend(get_childes(child))
    return childes


@cache
def get_parent_gesture(element):
    for g in get_pref().gesture:
        if element in g.element_iteration:
            return g
    raise Exception("没有拿到父级")


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
        return get_parent_element(self)

    @property
    def parent_gesture(self):
        return get_parent_gesture(self)

    @property
    def collection_iteration(self) -> list:
        items = []
        for e in self.parent_gesture.element:
            items.extend(get_childes(e))
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
        return get_childes(self)

    @property
    def selected_iteration(self):
        return self.parent_gesture.element_iteration

    # TODO Element Relationship Level
    @property
    def level(self) -> int:
        return 0


class ElementRelationship(Relationship,
                          PublicUniqueNamePropertyGroup,
                          PublicSortAndRemovePropertyGroup,
                          PublicOnlyOneSelectedPropertyGroup, ):
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
    def names_iteration(self):
        return self.parent_gesture.element_iteration

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

    def remove_before(self):
        for e in self.element:
            e.remove()
        return
