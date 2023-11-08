import bpy
from bpy.props import CollectionProperty
from bpy.types import PropertyGroup

from .element import Element
from .element.element_cure import ElementCURE
from .gesture_cure import GestureCURE
from .gesture_draw import GestureDraw
from .gesture_gpu_draw import GestureGpuDraw
from .gesture_keymap import GestureKeymap
from .gesture_property import GestureProperty
from .gesture_relationship import GestureRelationship
from ..public import PublicSortAndRemovePropertyGroup, PublicUniqueNamePropertyGroup


class Gesture(GestureCURE,
              GestureDraw,
              GestureGpuDraw,
              GestureKeymap,
              GestureProperty,
              GestureRelationship,
              PropertyGroup,
              PublicUniqueNamePropertyGroup,
              PublicSortAndRemovePropertyGroup
              ):
    # 使用gpu绘制在界面上
    element: CollectionProperty(type=Element)


classes_list = (
    Element,

    ElementCURE.ADD,
    ElementCURE.REMOVE,
    ElementCURE.MOVE,
    ElementCURE.SORT,

    Gesture,

    GestureCURE.ADD,
    GestureCURE.REMOVE,
    GestureCURE.SORT,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(classes_list)


def register():
    register_classes()


def unregister():
    unregister_classes()
