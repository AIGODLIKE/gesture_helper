from __future__ import annotations

from bpy.props import CollectionProperty, IntProperty
from bpy.types import PropertyGroup

from .element_cure import ElementCURE
from .element_draw import ElementDraw
from .element_gpu_draw import ElementGpuDraw
from .element_operator import ElementOperator
from .element_poll import ElementPoll
from .element_property import ElementProperty
from .element_relationship import ElementRelationship
from ..utils.public import PublicProperty
from ..utils.public_cache import cache_update_lock


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
    element: CollectionProperty(name='Child element', type=Element)
    index_element: IntProperty(name='Index')

    @cache_update_lock
    def __init_element__(self):
        getattr(self, f'__init_{self.element_type.lower()}__')()
