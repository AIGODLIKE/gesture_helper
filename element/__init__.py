from __future__ import annotations

import bpy
from bpy.props import CollectionProperty, IntProperty

from .element_cure import ElementCURE
from .element_draw import ElementDraw
from .element_gpu_draw import ElementGpuDraw, ElementGpuExtensionItem
from .element_operator import ElementOperator
from .element_poll import ElementPoll
from .element_property import ElementProperty
from .element_relationship import ElementRelationship
from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.structure_cache_ops import StructureCacheOps
from ..utils.property import __set_property__
from ..utils.public_cache import cache_update_lock, PublicCacheFunc
from ..utils.iteration import find_owning_gesture


# Nested child deletion handled separately
class Element(ElementCURE,
              ElementDraw,
              ElementGpuDraw,
              ElementGpuExtensionItem,
              ElementOperator,
              ElementPoll,
              ElementProperty,
              ElementRelationship,

              PrefAccess,
              ActiveSelection,
              StructureCacheOps,

              bpy.types.PropertyGroup):
    element: CollectionProperty(name='Child element', type=Element)
    index_element: IntProperty(name='Index')

    @cache_update_lock
    def __init_element__(self):
        gesture = find_owning_gesture(self)
        if gesture is not None:
            PublicCacheFunc.ensure_gesture_structure(gesture)
        getattr(self, f'__init_{self.element_type.lower()}__')()

    def __init_dividing_line__(self):
        self.name = "------------"

    def ___set_properties___(self, data):
        """Set operator_bl_idname before other operator properties when present."""
        if "operator_bl_idname" in data:
            self.operator_bl_idname = data["operator_bl_idname"]
        __set_property__(self, data)

    @property
    def name_translate(self) -> str:
        from ..src.translate import __name_translate__
        return __name_translate__(self.name)
