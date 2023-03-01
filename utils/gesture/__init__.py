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
from ..utils import PublicClass, PublicName, PublicIndex


class ElementOperator:
    class Add(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_add'
        bl_label = 'Add Ui Element'

        def execute(self, context: bpy.types.Context):
            new = self.active_element.ui_items.add()
            new.name = 'name'
            new['parent_element_items'] = self.active_element.name
            return {'FINISHED'}

    class Del(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_del'
        bl_label = 'Del Ui Element'

        @classmethod
        def poll(cls, context):
            return len(cls.pref_().element_items)

        def execute(self, context: bpy.types.Context):
            try:
                self.active_ui_element.remove(self.active_element.index)
            except Exception as e:
                log.info(e.args)
            return {'FINISHED'}

    class Copy(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_copy'
        bl_label = 'Add Ui Element'

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


class ElementItem(PropertyGroup,
                  PublicClass,
                  PublicIndex,
                  PublicName,
                  ElementOperator):  # 元素项
    ui_items: CollectionProperty(type=UiElementItems)
    active_index: IntProperty()

    @property
    def _items(self):
        return self.pref.gesture_element_items

    def copy(self):
        ...

    def move(self, to):
        ...

    def active_item(self):
        try:
            return self.ui_items[self.active_idnex]
        except IndexError as e:
            log.debug(f'active_element index error {e.args}')

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
class_tuple = (
    ElementItem,
    ElementItem.Add,
    ElementItem.Del,
    ElementItem.Copy,
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
