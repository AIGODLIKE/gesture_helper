import bpy
from bpy.props import CollectionProperty, BoolProperty, StringProperty
from bpy.types import PropertyGroup

from .gesture_cure import GestureCURE
from .gesture_draw import GestureDraw
from .gesture_keymap import GestureKeymap
from .gesture_property import GestureProperty
from .gesture_relationship import GestureRelationship
from ..element import Element
from ..element import ElementCURE
from ..utils.public import PublicProperty


class Gesture(GestureCURE,
              GestureDraw,
              GestureKeymap,
              GestureProperty,
              GestureRelationship,

              PublicProperty,

              PropertyGroup):
    # 使用gpu绘制在界面上
    element: CollectionProperty(type=Element)
    selected: BoolProperty(default=True)
    description: StringProperty(default="这是一个手势...")


classes_list = (
    Element,

    ElementCURE.ADD,
    ElementCURE.SORT,
    ElementCURE.COPY,
    ElementCURE.MOVE,
    ElementCURE.REMOVE,
    ElementCURE.ScriptEdit,
    ElementCURE.ScriptSave,

    Gesture,

    GestureCURE.ADD,
    GestureCURE.SORT,
    GestureCURE.COPY,
    GestureCURE.REMOVE,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(classes_list)


def register():
    register_classes()
    ElementCURE.ScriptSave.register_ui()


def unregister():
    unregister_classes()
    ElementCURE.ScriptSave.unregister_ui()
