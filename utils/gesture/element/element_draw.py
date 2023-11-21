# 绘制手势
# 预览绘制
import bpy

from ... import icon_two
from ...icons import Icons
from ...public import get_pref


class ElementDraw:
    def draw_item(self, layout: 'bpy.types.UILayout'):
        prop = get_pref().draw_property

        column = layout.column(align=True)

        split = column.split(factor=prop.element_split_factor)

        self.draw_item_left(split.row(align=True))

        right = split.row(align=True).split(factor=0.4)
        self.draw_item_right(right)
        right.prop(self, 'radio', text='')

        self.draw_item_child(column)

    def draw_item_left(self, layout: 'bpy.types.UILayout'):
        from ...icons import Icons
        pref = get_pref()
        row = layout.row()
        row.alert = self.is_show_alert
        row.prop(self,
                 'radio',
                 text='',
                 icon=icon_two(self.radio, 'RESTRICT_SELECT'),
                 emboss=False)
        if pref.draw_property.element_show_enabled_button:
            row.prop(self, 'enabled', text='')

        if self.is_operator:
            row.label(text='', icon='GEOMETRY_NODES')
        elif self.is_child_gesture:
            row.label(text='', icon='CON_CHILDOF')
        elif self.is_selected_structure:
            row.label(text='', icon_value=Icons.get(self.selected_type).icon_id)

        if self.is_child_gesture or self.is_operator:
            row.label(text='', icon_value=Icons.get(self.gesture_direction).icon_id)

    def draw_item_right(self, layout: 'bpy.types.UILayout'):
        layout.prop(self, 'name', text='')

        if len(self.element):
            layout.prop(self,
                        'show_child',
                        text='',
                        icon=icon_two(self.show_child, 'TRI'),
                        emboss=False)
        else:
            layout.separator()

    def draw_item_child(self, layout):
        if self.show_child and len(self.element):
            child = layout.box().column(align=True)
            child.enabled = self.enabled
            for element in self.element:
                element.draw_item(child)
            child.separator()

    def draw_item_property(self, layout: 'bpy.types.UILayout') -> None:
        if self.is_selected_structure:
            layout.prop(self, 'name')
            layout.label(text='选择结构', icon_value=Icons.get(self.selected_type).icon_id)
            layout.prop(self, 'poll_string')
            row = layout.row(align=True)
            row.prop(self, 'selected_type', expand=True)
        elif self.is_operator:
            layout.prop(self, 'name')
            layout.prop(self, 'operator_bl_idname')
            layout.prop(self, 'operator_context')
            layout.prop(self, 'operator_property', expand=True)
        elif self.is_child_gesture:
            layout.prop(self, 'name')
            layout.label(text='子手势', icon_value=Icons.get(self.gesture_direction).icon_id)
            layout.column().prop(
                self, 'gesture_direction',
                expand=True)

    def draw_debug(self, layout):
        layout.separator()
        layout.label(text=str(self))
        layout.label(text='index\t' + str(self.index))
        layout.label(text='parent_gesture\t' + str(self.parent_gesture))
        layout.label(text='parent_element\t' + str(self.parent_element))
        layout.label(text='operator_properties\t' + str(self.operator_properties))
        layout.label(text='collection_iteration\t' + str(self.collection_iteration))
        # layout.label(text='gesture_direction_items\t' + str(self.gesture_direction_items))
        layout.separator()
        for i in self.bl_rna.properties.keys():
            if i not in ('rna_type', 'name', 'relationship'):
                row = layout.row()
                row.label(text=i)
                row.prop(self, i, expand=True, )
