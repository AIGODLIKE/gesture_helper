import bpy.utils
from bpy.types import PropertyGroup
from bpy.props import CollectionProperty, IntProperty, BoolProperty

from bpy.props import EnumProperty
from . import ui_element

from .ui_element import UiElement

from ..public import PublicClass, register_module_factory
from ..public.public_data import PublicData
from ..public.public_property import PublicPropertyGroup, PublicNoRepeatName


class SystemItem(PublicClass,
                 PublicPropertyGroup,
                 PublicNoRepeatName,
                 ):
    """UI System Item
    """

    def set_active_index(self, index):
        self.pref.active_index = index

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        return self.pref.systems

    ui_element: CollectionProperty(type=UiElement)
    system_type: EnumProperty(items=PublicData.ENUM_UI_SYSTEM_TYPE)
    active_index: IntProperty(name='ui element active index')
    selected: BoolProperty(name='Selected Item')
    enabled: BoolProperty(name='Use this System')


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
