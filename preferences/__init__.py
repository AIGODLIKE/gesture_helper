from bpy.props import CollectionProperty, IntProperty, BoolProperty, PointerProperty, EnumProperty, FloatProperty
from bpy.types import Preferences, PropertyGroup

from .system import SystemItem
from ..public import PublicData


class UiProperty(PropertyGroup):
    default_factor = {
        'min': 0.15,
        'max': 0.9,
    }
    system_element_split_factor: FloatProperty(name="System Element Left Right Split Factor",
                                               default=0.5,
                                               **default_factor)

    system_split_factor: FloatProperty(name="System Item Split",
                                       default=0.5,
                                       **default_factor)

    element_split_factor: FloatProperty(name="Element Item Split",
                                        default=0.2,
                                        **default_factor,
                                        )
    child_element_office: IntProperty(name="UI Element Child Office Factor",
                                      default=50,
                                      min=10,
                                      max=250)


class PropertyPreferences:
    """inherited to addon preferences by this class
    """
    systems: CollectionProperty(name='UI Collection Items',
                                description='Element Item',
                                type=SystemItem
                                )
    active_index: IntProperty(name='gesture active index')
    enabled_systems: BoolProperty(name='Use all Systems')
    ui_property: PointerProperty(name='Ui Property',
                                 type=UiProperty,
                                 description="Control the display settings on the addon interface")
    addon_show_type: EnumProperty(items=PublicData.ENUM_ADDON_SHOW_TYPE)


class DrawPreferences(PropertyPreferences):
    ...


class GestureHelperPreferences(DrawPreferences, Preferences):
    ...


def register():
    ...


def unregister():
    ...
