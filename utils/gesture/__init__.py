import bpy.utils
from bpy.props import StringProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup, Operator

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
    ui_element_items: CollectionProperty(type=UiElementItems)
    active_index: IntProperty()

    def active_item(self):
        try:
            return self.ui_element_items[self.active_idnex]
        except IndexError as e:
            log.debug(f'active_element index error {e.args}')

    @property
    def index(self):
        return self.element_items.values().index(self)

    def register_key(self):
        ...

    def unregister_key(self):
        ...

    class Add(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_add'
        bl_label = 'Add Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'name'
            return {'FINISHED'}

    class Del(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_del'
        bl_label = 'Del Element'

        @classmethod
        def poll(cls, context):
            return len(cls.pref_().element_items)

        def execute(self, context: bpy.types.Context):
            try:
                self.element_items.remove(self.active_element.index)
            except Exception as e:
                log.info(e.args)
            return {'FINISHED'}

    class Copy(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_copy'
        bl_label = 'Add Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'name'
            return {'FINISHED'}

    class Export(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_export'
        bl_label = 'Export Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'Export  Element'
            return {'FINISHED'}

    class Import(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_import'
        bl_label = 'Import  Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'name'
            return {'FINISHED'}

    class Move(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_move'
        bl_label = 'Move Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'name'
            return {'FINISHED'}


mod_tuple = (
    draw,
    element,
    key,
    operator,
    prop,
)
class_tuple = (
    ElementItem,
    ElementItem.Add,
    ElementItem.Del,
    ElementItem.Copy,
    ElementItem.Export,
    ElementItem.Import,
    ElementItem.Move,
)
register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    for mod in mod_tuple:
        mod.register()

    register_class()


def unregister():
    for mod in mod_tuple:
        mod.unregister()
        
    unregister_class()
