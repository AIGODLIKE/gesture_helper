import bpy
from bpy.props import CollectionProperty, IntProperty
from bpy.types import PropertyGroup

from .element import Element
from .key import GestureKey
from ..public import PublicOperator, PublicProperty


class GestureCURE(PublicProperty):
    def new(self):
        return self.pref.gesture.add()

    def copy(self, from_element):
        ...

    def move(self, to_element):
        ...

    def sort(self, is_next):
        ...

    def remove(self):
        ...

    class ADD(PublicOperator):
        bl_idname = 'gesture.gesture_add'
        bl_label = '添加手势'

    class REMOVE(PublicOperator):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

    class MOVE(PublicOperator):
        bl_idname = 'gesture.gesture_move'
        bl_label = '移动手势'

    class SORT(PublicOperator):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'


class Gesture(PropertyGroup, GestureCURE, GestureKey):
    element: CollectionProperty(type=Element)
    element_index: IntProperty(name='索引')

    def draw(self, operator):
        ...


operator_list = (
    Element,
    Gesture,
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
