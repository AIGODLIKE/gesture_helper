from __future__ import annotations

import bpy
from mathutils import Vector

from .element_prop import ElementProp
from ...utils.public import PublicData
from ...utils.public.public_gpu import PublicGpu
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
        if self.parent_system.is_gesture_type:
            self.draw_edit_child_gestures(layout.box())
        box = layout.box()
        box.prop(self, 'text')
        box.prop(self, 'operator')
        box.prop(self, 'operator_property')
        box.prop(self, 'operator_context')
        self.draw_operator_property_set_layout(layout.box())

    def draw_edit_advanced_parameter(self, layout):  # TODO
        ...

    def draw_edit_poll_string(self, layout):
        from ...ops.ui_element_crud import ElementSetPollExpression
        width = bpy.context.area.width
        split = layout.split(factor=160 / width, align=True)

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

    def draw_edit_child_gestures(self, layout):
        layout.prop(self, 'text')
        layout.prop(self, 'gesture_position')
        if self.gesture_type_is_direction:
            layout.prop(self, 'gesture_direction')


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
            for child in self.wait_draw_children_element_items:
                child.draw_ui_layout(lay)

    def draw_ui_layout_prop(self, layout):
        ...

    def draw_ui_layout_operator(self, layout):
        ops = getattr(layout, self.type.lower(), None)
        self.set_operator_property_to(self.operator_property, ops)
        return ops

    def draw_ui_layout_menu(self, layout):
        ...

    def draw_ui_layout_child_gestures(self, layout):
        ...


class ElementDrawGesture(ElementProp, PublicGpu):
    direction: int
    is_about_beyond: bool
    width = 50
    height = 20
    ops: bpy.types.Operator

    @property
    def draw_start_point(self):
        ops = self.ops
        w, h = self.width, self.height
        c_w = w / 2
        c_h = h / 2

        direction_angle_maps = {
            1: (4, (-w, -c_h)),
            2: (0, (0, -c_h)),
            3: (-2, (-c_w, -h)),
            4: (2, (-c_w, 0)),
            5: (3, (-w, 0)),
            6: (1, (0, 0)),
            7: (-3, (-w, -h)),
            8: (-1, (0, -h)),
        }
        direction = direction_angle_maps[int(self.gesture_direction)]
        pie_radius = 120
        point = self.calculate_point_on_circle(ops.active_point, pie_radius, direction[0] * 45)
        return point + Vector(direction[1])

    def draw_gesture(self, ops, is_about_beyond: bool):
        self.is_about_beyond = is_about_beyond
        self.ops = ops

        # self.draw_2d_points([self.draw_start_point, ])
        self.draw_background()
        self.draw_text()
        self.draw_child_expand_icon()

    def draw_background(self):
        x, y = self.draw_start_point
        color = (0.329412, 0.329412, 0.329412, 1) if self.is_about_beyond else (0.094118, 0.094118, 0.094118, 1)
        self.draw_2d_rectangle(x, y, x + self.width, y + self.height, color=color)

    def draw_text(self):
        x, y = self.draw_start_point
        self.draw_2d_text(self.text, 15,
                          x, y + self.height,
                          color=(0.85098, 0.85098, 0.85098, 1))

    def draw_child_expand_icon(self):
        if self.gesture_is_direction_mode and self.gesture_is_have_child:
            from ...res import get_path
            o_x, y = self.draw_start_point
            w, h = self.width, self.height
            x = o_x + (w - h)
            self.draw_2d_image(get_path('images\\child_expand.png'), x, y, h, h)
