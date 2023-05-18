from __future__ import annotations

import bpy

from .element_prop import ElementProp
from ...ops.ui_element_crud import ElementSetPollExpression
from ...utils.public import PublicData
from ...utils.public.public_ui import PublicUi


class ElementDrawUIListItem(ElementProp):
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


class ElementDrawEdit(ElementProp,
                      PublicUi):
    def draw_active_ui_element_parameter(self, layout):
        act_type = self.type.lower()
        draw_edit_func = getattr(self, f'draw_edit_{act_type}', None)
        if draw_edit_func:
            draw_edit_func(layout)
            return

        for prop in self.UI_LAYOUT_INCOMING_ARGUMENTS[act_type]:
            draw_edit_func = getattr(self, f'draw_edit_{prop}', None)

            if draw_edit_func:
                draw_edit_func(layout)
            else:
                layout.prop(self, prop)

    def draw_edit_index(self, layout):  # TODO
        ...

    def draw_edit_icon(self, layout):  # TODO
        ...

    def draw_edit_operator(self, layout):
        # TODO 显示操作符label
        # TODO 自动设置为操作符label
        layout.prop(self, 'text')
        layout.prop(self, 'operator')
        layout.prop(self, 'operator_property')
        layout.prop(self, 'operator_context')
        self.draw_operator_property_set_layout(layout)

    def draw_edit_advanced_parameter(self, layout):  # TODO
        ...

    def draw_edit_poll_string(self, layout):
        width = bpy.context.area.width
        split = layout.split(factor=120 / width, align=True)

        split.prop(self, 'select_structure_type',
                   text='',
                   # icon='THREE_DOTS',
                   )

        row = split.row(align=True)
        row.prop(self, 'poll_string', text='')
        row.operator(ElementSetPollExpression.bl_idname,
                     text='',
                     icon='SETTINGS',
                     )

        is_extend, lay = self.draw_extend_ui(layout, 'poll_string_test', label='Show Poll Expand')
        if is_extend:
            lay.label(text='test')
            lay.label(text='test')
            lay.label(text='test')
            lay.label(text='test')


class ElementDrawUiLayout(ElementProp,
                          PublicData,
                          PublicUi):
    @property
    def ui_layout_args(self):
        return {i: self[i] for i in self.UI_LAYOUT_INCOMING_ARGUMENTS[self.type.lower()] if i in self}

    def draw_ui_layout(self, layout):
        ui_tp = self.type.lower()

        draw_func = getattr(self, f'draw_ui_layout_{ui_tp}', None)
        if self.is_select_structure_type:
            lay = layout
        elif draw_func:
            lay = draw_func(layout)
        else:
            lay = getattr(layout, ui_tp, None)(**self.ui_layout_args)

        if self.is_draw_child:
            for child in self.children_element:
                child.draw_ui_layout(lay)

    def draw_ui_layout_prop(self, layout):
        ...

    def draw_ui_layout_operator(self, layout):
        ops = getattr(layout, self.type.lower(), None)
        self.set_operator_property_to(self.operator_property, ops)
        return ops

    def draw_ui_layout_menu(self, layout):
        ...


class ElementDrawGesture(ElementProp):
    ...
