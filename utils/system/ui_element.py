from __future__ import annotations

import bpy
from bpy.props import EnumProperty, CollectionProperty, BoolProperty
from bpy.types import PropertyGroup

from ..public import PublicClass, PublicData
from ..public.public_property import PublicPropertyGroup
from ..public.public_ui import PublicUi


class ElementProp(PublicClass,
                  PublicPropertyGroup, ):
    ui_type: EnumProperty(items=PublicData.ENUM_UI_TYPE)
    ui_layout_type: EnumProperty(items=PublicData.ENUM_UI_LAYOUT_TYPE)
    select_structure_type: EnumProperty(items=PublicData.ENUM_SELECT_STRUCTURE_TYPE)
    children_element: CollectionProperty(type=UiElement)
    _selected_key = 'is_selected'

    def _get_selected(self):
        key = self._selected_key
        if key in self:
            return self[key]
        return False

    def _set_selected(self, value):
        key = self._selected_key
        # for i in self.parent_system.ui_element:
        #     ...
        self[key] = value
        print('set selected', value)

    def _update_selected(self, context):
        bpy.app.debug_events = True
        print('_update_selected')
        bpy.context.area.tag_redraw()
        bpy.app.debug_events = False

    is_expand: BoolProperty()
    is_enabled: BoolProperty(default=True)
    is_selected: BoolProperty(get=_get_selected, set=_set_selected,
                              update=_update_selected,
                              )

    @property
    def children_recursion(self):
        """反回递归所有子级"""
        recursion = []
        for child in self.children_element:
            recursion += [child, *child.children_recursion]
        return recursion

    @property
    def is_available(self) -> bool:
        return self.parent_system

    def set_active_index(self, index):
        self.parent_system.active_index = index

    @property
    def parent_system(self):
        systems = self.pref.systems.values()
        for s in systems:
            if self in s.children_element_recursion:
                return s

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        if self in self.parent_system.ui_element:
            return self.parent_system.ui_element  # 直接子项
        for element in self.parent_system.children_element_recursion:
            if self in element.children_element.values():
                return element.children_element  # 嵌套子项


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
        row.prop(self, 'ui_layout_type', text='')
        row.label(text=str(self.level))


class UiElement(ElementUi,
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
