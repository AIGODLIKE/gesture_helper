from bpy.types import PropertyGroup
from bpy.props import CollectionProperty, IntProperty

from .prop import GestureItem


class GestureProperty(PropertyGroup):
    gesture_system: CollectionProperty(name='Gesture Collection Items',
                                       description='Element Item',
                                       type=GestureItem
                                       )
    active_index: IntProperty(name='gesture active index')


def register():
    ...


def unregister():
    ...
