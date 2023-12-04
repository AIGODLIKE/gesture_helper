from __future__ import annotations

from bpy.props import CollectionProperty, StringProperty, IntProperty
from bpy.types import PropertyGroup

from .element_cure import ElementCURE
from .element_draw import ElementDraw
from .element_gpu_draw import ElementGpuDraw
from .element_operator import ElementOperator
from .element_poll import ElementPoll
from .element_property import ElementProperty
from .element_relationship import ElementRelationship
from ...public import PublicProperty


# 子元素的删除需要单独处理,是子级的子级,不能直接拿到
class Element(ElementCURE,
              ElementDraw,
              ElementGpuDraw,
              ElementOperator,
              ElementPoll,
              ElementProperty,
              ElementRelationship,

              PublicProperty,

              PropertyGroup):
    element: CollectionProperty(name='子级元素', type=Element)
    index_element: IntProperty(name='索引')

    def init(self):
        getattr(self, f'init_{self.element_type.lower()}')()
