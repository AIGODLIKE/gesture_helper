from __future__ import annotations

from bpy.props import CollectionProperty
from bpy.types import PropertyGroup

from .element_cure import ElementCURE
from .element_draw import ElementDraw
from .element_operator import ElementOperator
from .element_poll import ElementPoll
from .element_property import ElementProperty
from .element_relationship import ElementRelationship


# TODO 子元素的删除需要单独处理,是子级的子级,不能直接拿到
class Element(ElementCURE,
              ElementDraw,
              ElementOperator,
              ElementPoll,
              ElementProperty,
              ElementRelationship,

              PropertyGroup):
    element: CollectionProperty(name='子级元素', type=Element)
