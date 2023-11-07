import bpy

from .element import Element
from .element.element_cure import ElementCURE
from .gesture_cure import GestureCURE
from .gesture_draw import GestureDraw
from .gesture_gpu_draw import GestureGpuDraw
from .gesture_keymap import GestureKeymap
from .gesture_property import GestureProperty
from .gesture_relationship import GestureRelationship


class Gesture(GestureCURE,
              GestureDraw,
              GestureGpuDraw,
              GestureKeymap,
              GestureProperty,
              GestureRelationship):
    # 使用gpu绘制在界面上
    ...


operator_list = (
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

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
