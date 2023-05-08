from __future__ import annotations

import bpy
from bpy.types import PropertyGroup
from bpy.props import PointerProperty
from ..public import PublicClass


class UiElement(PropertyGroup, PublicClass):
    parent_element: PointerProperty(type=UiElement)


classes_tuple = (
    UiElement,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
