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
from ..property import (
    CUSTOM_UI_TYPE_ITEMS,
    UI_ELEMENT_TYPE_ENUM_ITEMS,
    UI_ELEMENT_SELECT_STRUCTURE_TYPE,
    SKIP_DEFAULT)
from ..utils import PublicClass, PublicName, PublicIndex, PublicMove, PublicPopup


class ElementOperator:
    class Add(PublicPopup, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_ui_add'
        bl_label = 'Add Ui Element'
        bl_description = '''\n默认将会添加作为活动元素子级\nCtrl 添加在同级之下\nShift 添加到无父级'''

        add_type: StringProperty()
        add_name: StringProperty()
        is_select_structure: BoolProperty(default=False,
                                          **SKIP_DEFAULT,
                                          )
        add_method: StringProperty(**SKIP_DEFAULT, )

        @classmethod
        def poll(cls, context):
            return len(cls.pref_().element_items)

        @property
        def element_enum(self):
            return UI_ELEMENT_SELECT_STRUCTURE_TYPE if self.is_select_structure else UI_ELEMENT_TYPE_ENUM_ITEMS

        @property
        def parent_element(self):
            act = self.active_ui_element
            if self.add_method == 'no_parent':
                return
            elif self.add_method == 'peer':
                return act.parent
            else:
                return act

        def draw_menu(self, menu, context):
            column = menu.layout.column(align=True)
            for identifier, name, _ in self.element_enum:
                if len(identifier):
                    op = column.operator(self.bl_idname, text=name)
                    op.add_name = 'New ' + name
                    op.add_type = identifier
                    op.add_method = self.add_method
                else:
                    column.separator()
                    column.label(text=name)

        def invoke(self, context, event):
            if event.ctrl:
                self.add_method = 'peer'
                self.title = '添加到同级'
            elif event.shift:
                self.title = '无父级'
                self.add_method = 'no_parent'
            else:
                self.title = ''
            log.debug(f'event {event.ctrl, event.shift, event.alt}')
            return super().invoke(context, event)

        def execute(self, context: bpy.types.Context):
            parent = self.parent_element

            new = self.active_element.ui_items_collection_group.add()
            new.set_name(self.add_name)
            new.ui_element_type = self.add_type
            new.parent = parent

            log.debug(f'ElementGroup add ui_element {new.name}\nparent:{parent}\nadd_type\t{self.add_type}\n')
            self.tag_redraw(context)
            return {'FINISHED'}

    class ElementCollectPoll:

        @classmethod
        def poll(cls, context):
            pref = cls.pref_()
            return pref.active_element and pref.active_ui_element

    class Del(Operator, PublicClass, ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_del'
        bl_label = 'Del Ui Element'
        bl_description = '删除元素\nCtrl 删除子级'

        def invoke(self, context: bpy.types.Context, event):
            self.active_ui_element.remove(remove_child=event.ctrl)
            self.tag_redraw(context)
            return {'FINISHED'}

    class Copy(Operator, PublicClass,
               ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_copy'
        bl_label = 'Add Ui Element'
        bl_description = '复制元素\nCtrl 复制子级'

        def invoke(self, context: bpy.types.Context, event):
            self.active_ui_element.copy(copy_child=event.ctrl)
            self.tag_redraw(context)
            return {'FINISHED'}

    class Move(Operator, PublicClass,
               ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_move'
        bl_label = 'Move Element'

        is_next: BoolProperty()

        def execute(self, context: bpy.types.Context):
            self.active_ui_element.move(is_next=self.is_next)
            self.tag_redraw(context)
            return {'FINISHED'}

    class MoveRelation(Operator, PublicClass,
                       ElementCollectPoll):
        bl_idname = 'gesture_helper.gesture_element_ui_move_relation'
        bl_label = 'Move relation'

        move_to: StringProperty()

        def to(self):
            self.active_element
            return self.move_to

        def execute(self, context: bpy.types.Context):
            # if self.move_to:
            #     self.active_ui_element.move_to()

            self.tag_redraw(context)
            return {'FINISHED'}


class ElementProperty(PublicClass,
                      PublicIndex,
                      PublicName,
                      PublicMove,
                      ElementOperator):
    element_type: EnumProperty(items=CUSTOM_UI_TYPE_ITEMS)

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
    def change_name(self, old_name, new_name):
        for i in self.ui_items_collection_group:
            i[self._parent_element_key] = new_name

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

    def update_ui_element(self):
        if len(self.ui_items_collection_group):
            self.ui_items_collection_group[-1].update()

    def copy(self):
        new = self.element_items.add()
        new.copy_from(self)
        new.name = self.name
        new.update_ui_element()
        
        log.debug(f'copy element {self.name} to {new.name}\n')

    def move(self, is_next=True):
        self.move_collection_element(self.element_items, self.pref, is_next=is_next)


class ElementGroup(ElementCRUD):  # 元素项
    ui_items_collection_group: CollectionProperty(type=UiCollectionGroupElement)

    @property
    def ui_draw_order(self):
        key = self._children_ui_element_not_parent_key
        ret = []
        collection = self.ui_items_collection_group
        for i in self[key]:
            item = collection[i]
            ret.append(item)
            ret.extend(item.children)
        return ret


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
    ElementGroup.MoveRelation,
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
