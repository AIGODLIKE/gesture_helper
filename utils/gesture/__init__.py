import bpy.utils
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, StringProperty
from bpy.types import PropertyGroup, Operator

from . import (
    draw,
    element,
    # key,
    operator,
    prop,
)
from .element import UiCollectionGroupElement
from ..log import log
from ..property import CUSTOM_UI_TYPE_ITEMS, UI_ELEMENT_TYPE_ENUM_ITEMS
from ..utils import PublicClass, PublicName, PublicIndex, PublicMove, PublicPopup


class ElementOperator:
    class Add(PublicPopup, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_add'
        bl_label = 'Add Ui Element'

        add_type: StringProperty()
        add_name: StringProperty()
        is_add_select_structure_type: BoolProperty()

        @classmethod
        def poll(cls, context):
            return len(cls.pref_().element_items)

        def draw_menu(self, menu, context):
            column = menu.layout.column(align=True)
            for identifier, name, _ in UI_ELEMENT_TYPE_ENUM_ITEMS:
                if len(identifier):
                    op = column.operator(self.bl_idname, text=name)
                    op.add_name = 'New ' + name
                    op.add_type = identifier
                else:
                    column.separator()
                    column.label(text=name)

        def execute(self, context: bpy.types.Context):
            new = self.active_element.ui_items_collection_group.add()
            new.set_name(self.add_name)
            new.ui_type = self.add_type
            log.debug(f'ElementGroup add ui_element {new.name}')
            return {'FINISHED'}

    class ElementCollectPoll:

        @classmethod
        def poll(cls, context):
            return cls.pref_().active_element

    class Del(Operator, PublicClass, ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_del'
        bl_label = 'Del Ui Element'

        def execute(self, context: bpy.types.Context):
            self.active_ui_element.remove()
            return {'FINISHED'}

    class Copy(Operator, PublicClass,
               ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_copy'
        bl_label = 'Add Ui Element'

        def execute(self, context: bpy.types.Context):
            self.active_ui_element.copy()
            return {'FINISHED'}

    class Move(Operator, PublicClass,
               ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_move'
        bl_label = 'Move Element'

        is_next: BoolProperty()

        def execute(self, context: bpy.types.Context):
            self.active_ui_element.move(is_next=self.is_next)
            return {'FINISHED'}


class ElementProperty(PublicClass,
                      PublicIndex,
                      PublicName,
                      PublicMove,
                      ElementOperator):
    def move(self, is_next=True):
        self.move_collection_element(self.element_items, self.pref, is_next=is_next)

    @property
    def _items(self):
        return self.pref.gesture_element_collection_group

    @property
    def _index_items(self):
        return self.ui_items_collection_group

    @property
    def _index(self):  # 用于删除时的索引
        return self.element_items.values().index(self)


class ElementCRUD(PropertyGroup,
                  ElementProperty):  # 增删查改
    def change_name(self, name):
        for i in self.ui_items_collection_group:
            i[self._parent_element_key] = name

    def remove(self):
        self.element_items.remove(self._index)

    def copy_from(self, item: 'ElementGroup'):
        self.active_index = item.active_index

        def copy_property(oring, to):
            bl_rna = getattr(oring, 'bl_rna', False)
            is_col = (type(oring).__name__ == 'bpy_prop_collection_idprop')

            if is_col:
                for i in oring:
                    n = to.add()
                    copy_property(i, n)
            elif bl_rna:
                for i in list(oring.keys()):
                    o = oring[i]
                    if type(o) in (float, int, str):
                        to[i] = o
                    elif type(o).__name__ == 'bpy_prop_collection_idprop':
                        copy_property(getattr(oring, i), getattr(to, i))

        copy_property(item.ui_items_collection_group, self.ui_items_collection_group)

    def copy(self):
        new = self.element_items.add()
        new.copy_from(self)
        new.name = self.name
        log.debug(f'copy element {self.name} to {new.name}\n')


class ElementGroup(ElementCRUD):  # 元素项
    ui_items_collection_group: CollectionProperty(type=UiCollectionGroupElement)
    element_type: EnumProperty(items=CUSTOM_UI_TYPE_ITEMS, )


mod_tuple = (
    draw,
    element,
    # key,
    operator,
    prop,
)
class_tuple = (
    ElementGroup,
    ElementGroup.Add,
    ElementGroup.Del,
    ElementGroup.Copy,
    ElementGroup.Move,
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
