from __future__ import annotations

import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup

from .ui_prop import ElementUILayoutProp, UIProp
from ...utils.public import PublicClass
from ...utils.public.public_data import ElementType, PublicData
from ...utils.public.public_property import PublicPropertyGroup
from ...utils.public.public_ui import PublicUi


class ElementProp(PublicClass,
                  ElementType,
                  PublicPropertyGroup,
                  ElementUILayoutProp,
                  UIProp,
                  ):
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
    def is_alert(self) -> bool:
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

    @property
    def is_draw(self) -> bool:
        """是否可绘制"""
        return self.is_enabled


class ElementLogic(ElementProp):
    is_available_select_structure: BoolProperty(name='是有效的选择结构', default=True, )

    @property
    def is_alert(self):
        is_sel = self.is_select_structure_type and self.is_available_select_structure
        is_ui = self.is_ui_layout_type
        return not (is_sel or is_ui)


class ElementCRUD(ElementLogic):

    def copy(self):
        add = self.parent_collection_property.add()
        self.set_property_data(add, self.props_data(self))
        self.parent_system.update_ui_layout()

    def remove(self):
        parent = self.parent_system
        super().remove()
        parent.update_ui_layout()

    def move(self, is_next=True):
        super().move(is_next)
        self.parent_system.update_ui_layout()


class ElementDrawEdit(ElementCRUD):
    level: int  # item nest level

    def draw_ui_list_item(self, layout, level):
        self.level = level
        layout.emboss = 'NONE'
        split = layout.row().split(factor=self.ui_prop.element_split_factor)
        # split.enabled = self.is_enabled

        self.draw_ui_list_item_lift(split)
        self.draw_ui_list_item_right(split)

        if self.is_expand:
            level += 1
            for child in self.children_element:
                child.draw_ui_list_item(layout, level)

    def draw_ui_list_item_lift(self, layout):
        row = self.space_layout(layout, self.ui_prop.child_element_office, self.level).row(align=True)
        row.alert = self.is_alert
        row.prop(self, 'is_enabled', text='', icon=self.icon_two(self.is_enabled, 'CHECKBOX'))
        if len(self.children_element):
            row.prop(self, 'is_expand', text='', icon=self.icon_two(self.is_expand, 'TRIA'))

    def draw_ui_list_item_right(self, layout):
        row = layout.row(align=True)
        sel = row.row(align=True)
        sel.alert = self.is_alert
        sel.prop(self, 'is_selected', text='', icon=self.icon_two(self.is_selected, 'RESTRICT_SELECT'))
        name = row.row()
        name.emboss = 'NORMAL'
        name.prop(self, 'name', text='')
        row.label(text=self.type)
        row.label(text=str(self.level))

    def draw_active_ui_element_parameter(self, layout):
        act_type = self.type.lower()
        if act_type in ('',):
            getattr(self, f'draw_edit_{act_type}', None)(layout)
            return

        for prop in self.UI_LAYOUT_INCOMING_ARGUMENTS[act_type]:
            if prop in ('index',):
                getattr(self, f'draw_edit_{prop}', None)(layout)
            else:
                layout.prop(self, prop)

    def draw_edit_index(self, layout):  # TODO
        ...

    def draw_edit_icon(self, layout):  # TODO
        ...

    def draw_advanced_parameter(self, layout):  # TODO
        ...


class ElementDrawUiLayout(ElementDrawEdit,
                          PublicData,
                          PublicUi):
    @property
    def ui_layout_args(self):
        return {i: self[i] for i in self.UI_LAYOUT_INCOMING_ARGUMENTS[self.type.lower()] if i in self}

    def draw_ui_layout(self, layout):
        ui_tp = self.type.lower()

        if self.is_select_structure_type:
            lay = layout
        else:
            lay = getattr(layout, ui_tp, None)(**self.ui_layout_args)

        if self.is_draw:
            for child in self.children_element:
                child.draw_ui_layout(lay)


class UiElement(ElementDrawUiLayout,
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
