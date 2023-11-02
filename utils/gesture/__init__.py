from functools import cache

import bpy
from bpy.props import CollectionProperty, IntProperty, StringProperty, BoolProperty

from .element import Element, ElementCURE
from .key import GestureKey
from ..public import PublicOperator, PublicProperty, PublicUniqueNamePropertyGroup, get_pref


class GestureCURE(PublicProperty, GestureKey):
    # def copy(self, from_element):
    #     ...
    # def sort(self, is_next):
    #     ...

    @property
    def index(self):
        return get_element_index(self)

    def remove(self):
        self.unload_key()
        self.pref.gesture.remove(self.index)

    class ADD(PublicOperator):
        bl_idname = 'gesture.gesture_add'
        bl_label = '添加手势'

        def execute(self, context):
            add = self.pref.gesture.add()
            add.name = 'Gesture'
            return {"FINISHED"}

    class REMOVE(PublicOperator):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

        def execute(self, context):
            self.pref.active_gesture.remove()
            return {"FINISHED"}

    class SORT(PublicOperator):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, context):
            return {"FINISHED"}


@cache
def get_element_iteration(gesture: '[Element]') -> [Element]:
    items = []
    for e in gesture:
        items.extend(e.element_iteration)
    return items


@cache
def get_element_index(gesture: 'Gesture') -> int:
    return gesture.pref.gesture.values().index(gesture)


class Gesture(
    PublicUniqueNamePropertyGroup,
    GestureCURE,
):
    element: CollectionProperty(type=Element)
    index_element: IntProperty(name='索引')

    # TODO 启用禁用整个系统,主要是keymap
    enable: BoolProperty(name='启用此手势')

    @property
    def element_iteration(self) -> [Element]:
        return get_element_iteration(self.element)

    @property
    def _items_iteration(self):
        return get_pref().gesture.values()

    def draw(self, operator):
        ...


operator_list = (
    ElementCURE.ADD,
    ElementCURE.DEL,
    ElementCURE.MOVE,
    ElementCURE.SORT,

    Element,

    GestureCURE.ADD,
    GestureCURE.REMOVE,
    GestureCURE.SORT,
    Gesture,
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
