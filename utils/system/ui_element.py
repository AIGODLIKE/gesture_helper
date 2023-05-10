from __future__ import annotations

from functools import cache

import bpy
from bpy.props import EnumProperty
from bpy.types import PropertyGroup

from ..public import PublicClass, PublicData
from ..public.public_property import PublicPropertyGroup, PublicCollectionNoRepeatName, PublicRelationship


class UiElement(PublicClass,
                PublicCollectionNoRepeatName,
                PublicRelationship,
                PublicPropertyGroup,
                ):
    ui_type: EnumProperty(items=PublicData.ENUM_UI_TYPE)
    ui_layout_type: EnumProperty(items=PublicData.ENUM_UI_LAYOUT_TYPE)
    select_structure_type: EnumProperty(items=PublicData.ENUM_SELECT_STRUCTURE_TYPE)

    @property
    def is_available(self) -> bool:
        return self.parent_system

    def set_active_index(self, index):
        self.parent_system.active_index = index

    @property
    def parent_system(self):
        systems = self.pref.systems.values()
        for s in systems:
            if self in s.ui_element.values():
                return s

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        if self.parent_system:
            return self.parent_system.ui_element


classes_tuple = (
    UiElement,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
