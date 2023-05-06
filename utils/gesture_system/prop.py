import bpy.utils
from bpy.props import EnumProperty
from bpy.types import PropertyGroup


class GestureItem(PropertyGroup):
    system_type: EnumProperty(items='')
    ...


def register():
    bpy.utils.register_class(GestureItem)


def unregister():
    bpy.utils.unregister_class(GestureItem)
