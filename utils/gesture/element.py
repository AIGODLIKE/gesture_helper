from __future__ import annotations

from functools import cache

from bpy.props import CollectionProperty, BoolProperty, IntProperty

from ..public import (
    PublicOnlyOneSelectedPropertyGroup,
    PublicUniqueNamePropertyGroup,
    PublicProperty,
    PublicOperator,
    get_pref
)


class ElementCURE(PublicProperty):
    class ADD(PublicOperator):
        bl_idname = 'gesture.element_add'
        bl_label = '添加手势项'

        def execute(self, context):
            add = self.pref.active_gesture.element.add()
            add.name = 'Element'
            return {"FINISHED"}

    class REMOVE(PublicOperator):
        bl_idname = 'gesture.element_remove'
        bl_label = '删除手势项'

        def execute(self, context):
            self.pref.active_element.remove()
            return {"FINISHED"}

    class MOVE(PublicOperator):
        bl_idname = 'gesture.element_move'
        bl_label = '移动手势项'

        def execute(self, context):
            return {"FINISHED"}

    class SORT(PublicOperator):
        bl_idname = 'gesture.element_sort'
        bl_label = '排序手势项'

        is_next: BoolProperty()

        def execute(self, context):
            return {"FINISHED"}


@cache
def get_childes(item: Element):
    childes = item.element.items()
    if len(childes):
        for child in childes:
            childes.extend(get_childes(child))
    childes.append(item)
    return childes


@cache
def get_parent_gesture(element: 'Element') -> 'Gesture':
    try:
        pref = get_pref()
        for g in pref.gesture:
            if element in g.element_iteration:
                return g
    except IndexError:
        ...


@cache
def get_parent_element(element: 'Element') -> 'Element':
    for e in element.parent_gesture.element_iteration:
        if element in e.element:
            return e


@cache
def get_element_index(element: 'Element') -> int:
    return element.parent_element.element.values().index(element)


class ElementProperty(ElementCURE,
                      PublicUniqueNamePropertyGroup,
                      PublicOnlyOneSelectedPropertyGroup):
    index_element: IntProperty()
    enable: BoolProperty(name='启用', default=True)

    element: CollectionProperty(type=Element)

    @property
    def index(self):
        return get_element_index(self)

    @property
    def parent_element(self):
        return get_parent_element(self)

    @property
    def parent_gesture(self):
        return get_parent_gesture(self)

    @property
    def _items_iteration(self):
        items = []
        for e in self.parent_gesture.element:
            items.extend(get_childes(e))
        return items

    @property
    def element_iteration(self) -> [Element]:
        return get_childes(self)


# TODO 子元素的删除需要单独处理,是子级的子级,不能直接拿到
class Element(ElementProperty):
    ...
