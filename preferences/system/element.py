from __future__ import annotations

import bpy
from bpy.props import CollectionProperty, IntProperty
from bpy.types import PropertyGroup

from .element_draw import ElementDrawEdit, ElementDrawGesture, ElementDrawUIListItem, ElementDrawUiLayout
from .element_prop import ElementProp


class ElementLogic(ElementProp):
    def _get_self_src(self, key):
        func = getattr(self, f'is_{key}_{self.ui_type.lower()}', getattr(self, f'is_{key}_{self.type.lower()}', None))
        if isinstance(func, bool):
            return func
        elif getattr(func, '__call__', None):
            return func()

    @property
    def is_alert(self):
        alert_pr = self._get_self_src('alert')
        if alert_pr:
            return alert_pr
        is_sel = self.is_select_structure_type and self.is_available_select_structure
        is_ui = self.is_ui_layout_type
        is_ges = self.is_gesture_type
        return not (is_sel or is_ui or is_ges)

    @property
    def is_available(self):
        """是可用的"""
        available_pr = self._get_self_src('available')
        if available_pr:
            return available_pr
        return True


class ElementCRUD(ElementProp):

    def copy(self):
        add = self.parent_collection_property.add()
        self.set_property_data(add, self.props_data(self))
        add.parent_system.update_ui_layout()

    def remove(self):
        parent = self.parent_system
        super().remove()
        parent.update_ui_layout()

    def move(self, is_next=True):
        super().move(is_next)
        self.parent_system.update_ui_layout()


class ElementRelationship(ElementProp):

    def update_index(self, context):
        if self.parent_element:
            index = self['active_index']
            self.parent_element.children_element[index].is_selected = True

    active_index: IntProperty(update=update_index)

    children_element: CollectionProperty(type=UiElementItem)

    @property
    def children_recursion(self) -> 'list[UiElementItem]':
        """反回递归所有子级"""
        recursion = []
        for child in self.children_element:
            recursion += [child, *child.children_recursion]
        return recursion

    def set_active_index(self, index) -> None:
        if self.is_direct_child:
            self.parent_system.active_index = index
        else:
            self.parent_element.active_index = index

    @property
    def parent_system(self):
        systems = self.pref.systems.values()
        for s in systems:
            if self in s.children_element_recursion:
                return s

    @property
    def parent_element(self) -> 'UiElementItem':
        if self.is_nest_child:
            for element in self.parent_system.children_element_recursion:
                if self in element.children_element.values():
                    return element

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        if self.is_direct_child:
            return self.parent_system.ui_element  # 直接子级
        for element in self.parent_system.children_element_recursion:
            if self in element.children_element.values():
                return element.children_element  # 嵌套子级

    @property
    def is_nest_child(self) -> bool:
        """是嵌套子级
        a----
         this-
        """
        return not self.is_direct_child

    @property
    def is_direct_child(self) -> bool:
        """
        :return:
        """
        return self in self.parent_system.ui_element.values()


class UiElementItem(ElementCRUD,
                    ElementLogic,

                    ElementDrawEdit,
                    ElementDrawGesture,
                    ElementDrawUiLayout,
                    ElementDrawUIListItem,

                    ElementRelationship,

                    ElementProp,
                    ):

    def update_select_structure_type(self, context):
        self.parent_system.update_ui_layout()

    @property
    def wait_draw_children_element_items(self) -> 'iter':
        """等待绘制项,在绘制时"""
        return self.parent_system._get_wait_draw_gesture_items(self.children_element)


classes_tuple = (
    UiElementItem,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
