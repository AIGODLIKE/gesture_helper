import bpy.utils
from bpy.types import PropertyGroup
from bpy.props import CollectionProperty, IntProperty

from bpy.props import EnumProperty
from . import ui_element

from .ui_element import UiElement

from ..public import PublicClass, register_module_factory
from ..public.public_data import PublicData


class SystemItem(PropertyGroup, PublicClass):
    """UI System Item
    """
    ui_element: CollectionProperty(type=UiElement)
    system_type: EnumProperty(items=PublicData.ENUM_TYPE_UI_SYSTEM)
    active_index: IntProperty(name='ui element active index')


classes_tuple = (
    SystemItem,
)
modules_tuple = (
    ui_element,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)
register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()
    register_class()


def unregister():
    unregister_mod()
    unregister_class()
