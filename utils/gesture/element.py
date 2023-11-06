from __future__ import annotations

from functools import cache

import bpy
from bpy.props import CollectionProperty, BoolProperty

from .prop import ElementProperty
from .. import icon_two
from ..public import (
    PublicOnlyOneSelectedPropertyGroup,
    PublicUniqueNamePropertyGroup,
    PublicOperator,
    get_pref, PublicSortAndRemovePropertyGroup
)


class ElementCURE(ElementProperty):
    class ElementPoll(PublicOperator):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_element is not None

    class ADD(PublicOperator):
        bl_idname = 'gesture.element_add'
        bl_label = '添加手势项'

        def execute(self, context):
            add = self.pref.active_gesture.element.add()
            add.name = 'Element'
            return {"FINISHED"}

    class REMOVE(ElementPoll):
        bl_idname = 'gesture.element_remove'
        bl_label = '删除手势项'

        def execute(self, context):
            self.pref.active_element.remove()
            return {"FINISHED"}

    class MOVE(ElementPoll):
        bl_idname = 'gesture.element_move'
        bl_label = '移动手势项'

        def execute(self, context):
            return {"FINISHED"}

    class SORT(ElementPoll):
        bl_idname = 'gesture.element_sort'
        bl_label = '排序手势项'

        is_next: BoolProperty()

        def execute(self, _):
            self.active_element.sort(self.is_next)
            return {"FINISHED"}


@cache
def get_childes(item: Element):
    childes = item.element.values()
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
        if element in e.element.values():
            return e


@cache
def get_element_index(element: 'Element') -> int:
    return element.collection.values().index(element)


class ElementProperty(ElementCURE,
                      PublicUniqueNamePropertyGroup,
                      PublicSortAndRemovePropertyGroup,
                      PublicOnlyOneSelectedPropertyGroup):
    enabled: BoolProperty(name='启用', default=True)

    element: CollectionProperty(type=Element)

    def _get_index(self) -> int:
        return get_element_index(self)

    def _set_index(self, value):
        if self.is_root:
            self.parent_gesture['index_element'] = self.index
            print('_set_index', value)

    index = property(
        fget=_get_index,
        fset=_set_index,
        doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def parent_element(self) -> 'Element':
        return get_parent_element(self)

    @property
    def parent_gesture(self) -> 'Gesture':
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
    def element_iteration(self) -> [Element]:
        return get_childes(self)

    @property
    def selected_iteration(self) -> [Element]:
        return self.parent_gesture.element_iteration

    @property
    def is_root(self):
        return self in self.parent_gesture.element.values()


# TODO 子元素的删除需要单独处理,是子级的子级,不能直接拿到
class Element(ElementProperty):
    def selected_update(self, context):
        """
        在选择其它子项的时候自动将活动索引切换
        @rtype: object
        """
        for (element, index) in enumerate(self.parent_gesture.element):
            if self in element.collection_iteration:
                self.parent_gesture['index_element'] = self.index

    def draw_ui(self, layout: 'bpy.types.UILayout') -> None:
        layout.prop(self, 'enabled', text='', emboss=False)
        layout.prop(self,
                    'selected',
                    text='',
                    icon=icon_two(self.selected, 'RESTRICT_SELECT'),
                    emboss=False
                    )
        layout.prop(self, 'name')

    def draw_ui_property(self, layout: 'bpy.types.UILayout') -> None:
        layout.prop(self, 'name')

        self.draw_debug(layout)

    def draw_debug(self, layout):
        layout.label(text=str(self))
        layout.label(text=str(self.index))
        layout.label(text=str(self.parent_gesture))
        layout.label(text=str(self.parent_element))
        layout.label(text=str(self.collection_iteration))
