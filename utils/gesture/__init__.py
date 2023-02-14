import bpy.utils
from bpy.props import StringProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup

from .element import UiElementItems
from ..log import log
from . import (
    draw,
    element,
    key,
    operator,
    prop,
)
from ..utils import PublicClass


class ElementItem(PropertyGroup, PublicClass):
    def get_name(self):
        if 'name' not in self:
            return 'emm'
        return self['name']

    def set_name(self, value):
        self['name'] = value

    def update_name(self, context):
        log.debug(f'update {self}')

    name: StringProperty(
        name='emm',
        get=get_name,
        set=set_name,
        update=update_name,
    )
    ui_element: CollectionProperty(type=UiElementItems)
    active_index: IntProperty()

    @property
    def index(self):
        return self.element_items.values().index(self)

    def register_key(self):
        ...

    def unregister_key(self):
        ...


mod_tuple = (
    draw,
    element,
    key,
    operator,
    prop,
)


def register():
    for mod in mod_tuple:
        mod.register()

    bpy.utils.register_class(ElementItem)


def unregister():
    for mod in mod_tuple:
        mod.unregister()

    bpy.utils.unregister_class(ElementItem)
