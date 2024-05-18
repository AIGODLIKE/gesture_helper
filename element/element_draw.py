# 绘制手势
# 预览绘制
import bpy

from . import ElementCURE
from ..ops.set_direction import SetDirection
from ..utils.icons import Icons
from ..utils.public import get_pref
from ..utils.public_ui import icon_two


class ElementDraw:
    def draw_item(self, layout: 'bpy.types.UILayout'):
        pref = get_pref()
        draw = pref.draw_property
        other = pref.other_property

        layout.context_pointer_set('move_element', self)
        column = layout.column(align=True)

        split = column.split(factor=draw.element_split_factor)

        self.draw_item_left(split.row(align=True))

        right = split.row(align=True).split(factor=0.4)
        self.draw_item_right(right)
        right.prop(self, 'radio', text='',
                   icon=icon_two(self.radio, 'RESTRICT_SELECT'),
                   emboss=False)
        if other.is_move_element:
            from .. import ElementCURE
            r = right.row()
            r.enabled = self.is_movable
            r.operator(ElementCURE.MOVE.bl_idname, text="", icon="HANDLETYPE_AUTO_CLAMP_VEC")

        self.draw_item_child(column)

    def draw_item_left(self, layout: 'bpy.types.UILayout'):
        pref = get_pref()
        row = layout.row()
        row.alert = self.is_show_alert
        if pref.draw_property.element_show_enabled_button:
            row.prop(self, 'enabled', text='')

        if self.is_operator:
            row.label(text='', icon='GEOMETRY_NODES')
        elif self.is_child_gesture:
            row.label(text='', icon='CON_CHILDOF')
        elif self.is_selected_structure:
            row.label(text='', icon_value=Icons.get(self.selected_type).icon_id)

        if self.is_child_gesture or self.is_operator:
            row.label(text='', icon_value=Icons.get(self.direction).icon_id)
        else:
            row.separator()
            row.separator()

    def draw_item_right(self, layout: 'bpy.types.UILayout'):
        layout.prop(self, 'name', text='')

        if len(self.element):
            layout.prop(self,
                        'show_child',
                        text='',
                        icon=icon_two(self.show_child, 'TRI'),
                        emboss=False)
        else:
            layout.prop(self, 'radio', text='', icon='NONE', emboss=False)

    def draw_item_child(self, layout):
        if self.show_child and len(self.element):
            child = layout.box().column(align=True)
            child.enabled = self.enabled
            for element in self.element:
                element.draw_item(child)
            child.separator()

    def draw_item_property(self, layout: 'bpy.types.UILayout') -> None:

        if self.is_selected_structure:
            from ..ops.set_poll import SetPollExpression
            icon = Icons.get(self.selected_type).icon_id

            layout.prop(self, 'name')

            row = layout.row()
            row.label(text='选择结构', icon_value=icon)
            row.operator(SetPollExpression.bl_idname)
            layout.prop(self, 'poll_string')
            row = layout.row(align=True)
            row.prop(self, 'selected_type', expand=True)
        elif self.is_operator:
            is_operator = self.operator_type == 'OPERATOR'
            preview_script = self.preview_operator_script
            row = layout.row(align=True)
            col = row.column()
            col.prop(self, 'name')
            col.prop(self, 'operator_type')
            if is_operator:
                col.prop(self, 'operator_bl_idname')
                col.prop(self, 'operator_properties')
            else:
                col.operator(ElementCURE.ScriptEdit.bl_idname)
                rr = col.row(align=True)
                rr.label(text=f"脚本字数:{len(self.operator_script)}")
                rr.separator_spacer()
                rr.prop(self, 'preview_operator_script', icon_only=True, icon=icon_two(preview_script, style="HIDE"),
                        emboss=False)
            SetDirection.draw_direction(row.column())

            if is_operator:
                row = layout.row(align=True)
                row.prop(self, 'operator_context')
                row.prop(self.other_property, 'auto_update_element_operator_properties', icon='FILE_REFRESH', text='')
                row.prop(self, 'operator_properties_sync_from_temp_properties', icon='SORT_DESC')
                row.prop(self, 'operator_properties_sync_to_properties', icon='SORT_ASC')
                layout.box().template_keymap_item_properties(self.operator_tmp_kmi)
                if self.other_property.auto_update_element_operator_properties:
                    self.from_tmp_kmi_operator_update_properties()
            else:
                if preview_script:
                    script_box = layout.box()
                    for i in self.operator_script.split('\n'):
                        script_box.label(text=i)

        elif self.is_child_gesture:
            row = layout.row(align=True)
            column = row.column()
            column.prop(self, 'name')
            column.label(text='子手势', icon_value=Icons.get(self.direction).icon_id)
            SetDirection.draw_direction(row.column())

    def draw_debug(self, layout):
        layout.separator()
        layout.label(text=str(self))
        layout.label(text='index\t' + str(self.index))
        layout.label(text='parent_gesture\t' + str(self.parent_gesture))
        layout.label(text='parent_element\t' + str(self.parent_element))
        layout.label(text='operator_properties\t' + str(self.operator_properties))
        layout.label(text='collection_iteration\t' + str(self.collection_iteration))
        layout.label(text='gesture gesture_direction_items\t' + str(self.active_gesture.gesture_direction_items))
        layout.label(text='element gesture_direction_items\t' + str(self.gesture_direction_items))
        layout.separator()
        for i in self.bl_rna.properties.keys():
            if i not in ('rna_type', 'name', 'relationship'):
                row = layout.row()
                row.label(text=i)
                row.prop(self, i, expand=True, )
