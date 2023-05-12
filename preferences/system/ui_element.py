from __future__ import annotations

import bpy
from bpy.props import CollectionProperty, BoolProperty, IntProperty
from bpy.types import PropertyGroup

from ...utils.public import PublicClass
from ...utils.public.public_data import ElementType
from ...utils.public.public_property import PublicPropertyGroup
from ...utils.public.public_ui import PublicUi


class ElementProp(PublicClass,
                  ElementType,
                  PublicPropertyGroup, ):
    children_element: CollectionProperty(type=UiElement)

    def update_index(self, context):
        if self.parent_element:
            index = self['active_index']
            self.parent_element.children_element[index].is_selected = True

    active_index: IntProperty(update=update_index)
    _selected_key = 'is_selected'

    def _get_selected(self) -> bool:
        key = self._selected_key
        if key in self:
            return self[key]
        return False

    def _set_selected(self, value) -> None:
        key = self._selected_key
        for element in self.parent_system.children_element_recursion:
            element['is_selected'] = (element == self)
        self[key] = value

    def _update_selected(self, context) -> None:
        ...

    is_expand: BoolProperty(name='Expand Show Child Element',
                            default=True)
    is_enabled: BoolProperty(name='Enabled Element Show, If False Not Show Child And Draw',
                             default=True)
    is_selected: BoolProperty(get=_get_selected,
                              set=_set_selected,
                              update=_update_selected,
                              )

    @property
    def children_recursion(self) -> 'list[UiElement]':
        """反回递归所有子级"""
        recursion = []
        for child in self.children_element:
            recursion += [child, *child.children_recursion]
        return recursion

    @property
    def is_available(self) -> bool:
        return self.parent_system

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
    def parent_element(self) -> 'UiElement':
        if self.is_nest_child:
            for element in self.parent_system.children_element_recursion:
                if self in element.children_element:
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


class ElementUi(ElementProp,
                PublicUi,
                ):
    level: int  # item nest level

    def draw(self, layout, level):
        self.level = level
        layout.emboss = 'NONE'
        split = layout.row().split(factor=self.ui_prop.element_split_factor)
        # split.enabled = self.is_enabled

        self.draw_lift(split)
        self.draw_right(split)

        if self.is_expand:
            level += 1
            for child in self.children_element:
                child.draw(layout, level)

    def draw_lift(self, layout):
        row = self.space_layout(layout, self.ui_prop.child_element_office, self.level).row(align=True)
        row.prop(self, 'is_enabled', text='', icon=self.icon_two(self.is_enabled, 'CHECKBOX'))
        if len(self.children_element):
            row.prop(self, 'is_expand', text='', icon=self.icon_two(self.is_expand, 'TRIA'))

    def draw_right(self, layout):
        row = layout.row(align=True)
        row.prop(self, 'is_selected', text='', icon=self.icon_two(self.is_selected, 'RESTRICT_SELECT'))
        name = row.row()
        name.emboss = 'NORMAL'
        name.prop(self, 'name', text='')
        row.label(text=self.type)
        row.label(text=str(self.level))


class ElementLogic(ElementUi):
    ...


class ElementDrawEdit(ElementLogic):
    ...


class ElementDrawLayout(ElementDrawEdit):
    ...


class UiElement(ElementDrawLayout,
                ):
    ...


classes_tuple = (
    UiElement,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
