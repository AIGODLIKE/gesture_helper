# 绘制手势
# 预览绘制
from bpy.app.translations import pgettext_iface

from . import ElementCURE
from ..ops.set_direction import SetDirection
from ..utils.public import get_pref
from ..utils.public_ui import icon_two


class ElementDraw:
    def draw_item(self, layout: 'bpy.types.UILayout'):
        pref = get_pref()
        draw = pref.draw_property

        layout.context_pointer_set('move_element', self)
        layout.context_pointer_set('cut_element', self)

        column = layout.column(align=True)

        split = column.split(factor=draw.element_split_factor)
        split.alert = self.is_alert
        self.draw_item_left(split.row(align=True))

        right = split.row(align=True).split(factor=0.4)
        self.draw_item_right(right)
        right.prop(self, 'radio', text='',
                   icon=icon_two(self.radio, 'RESTRICT_SELECT'),
                   emboss=False)

        if pref.__is_move_element__:
            from .element_cure import ElementCURE
            r = right.row()
            r.active = r.enabled = self.is_movable
            r.operator(ElementCURE.MOVE.bl_idname, text="", icon="UV_SYNC_SELECT", emboss=False)
        elif pref.__is_cut_element__:
            from .element_cure import ElementCURE
            r = right.row()
            r.active = r.enabled = self.is_can_be_cut
            r.operator(ElementCURE.CUT.bl_idname, text="", icon="PASTEFLIPDOWN", emboss=False)
        self.draw_item_child(column)

    def draw_item_left(self, layout: 'bpy.types.UILayout'):
        pref = get_pref()
        row = layout.row()
        if pref.draw_property.element_show_enabled_button:
            row.prop(self, 'enabled', text='')
        if self.is_operator:
            row.label(text='', icon='GEOMETRY_NODES')
        elif self.is_child_gesture:
            row.label(text='', icon='CON_CHILDOF')
        elif self.is_selected_structure:
            row.label(text='', icon_value=pref.__get_icon__(self.selected_type))
        elif self.is_dividing_line:
            row.label(text='', icon_value=pref.__get_icon__("REMOVE"))

        if self.parent_is_extension:  # 下面的展开项不显示图标
            if self.is_child_gesture:
                row.label(text='', icon_value=pref.__get_icon__("MENU_PANEL"))
            else:
                row.separator()
                row.separator()
        elif self.is_child_gesture or self.is_operator:
            row.label(text='', icon_value=pref.__get_icon__(self.direction))
        else:
            row.separator()
            row.separator()

    def draw_item_right(self, layout: 'bpy.types.UILayout'):
        layout.label(text=self.name_translate, translate=False)

        if len(self.element):
            layout.prop(self,
                        'show_child',
                        text='',
                        icon=icon_two(self.show_child, 'TRI'),
                        emboss=False)
        else:
            layout.prop(self, 'radio', text='', icon='NONE', emboss=False)
        self.draw_icon(layout)

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
            icon = self.pref.__get_icon__(self.selected_type)

            layout.prop(self, 'name')

            row = layout.row()
            row.label(text='Select structure', icon_value=icon)
            row.operator(SetPollExpression.bl_idname)
            layout.prop(self, 'poll_string')
            row = layout.row(align=True)
            row.prop(self, 'selected_type', expand=True)
        elif self.is_operator:
            self.draw_operator(layout)
        elif self.is_child_gesture:
            row = layout.row(align=True)
            column = row.column()
            column.prop(self, 'name')
            self.draw_edit_icon(column)
            column.label(text='Child gesture', icon_value=self.pref.__get_icon__(self.direction))

            if not self.parent_is_extension:  # 如果是展开菜单就不显示方向设置
                SetDirection.draw_direction(row.column())

    def draw_debug(self, layout):
        """
        # layout.label(text='gesture gesture_direction_items\t' + str(self.active_gesture.gesture_direction_items))
        使用blender 绘制此属性时poll会出现错误
        :param layout:
        :return:
        """
        layout.separator()
        layout.label(text=str(self))
        layout.label(text='index\t' + str(self.index))
        layout.label(text='parent_gesture\t' + str(self.parent_gesture))
        layout.label(text='parent_element\t' + str(self.parent_element))
        layout.label(text='operator_properties\t' + str(self.operator_properties))
        layout.label(text='collection_iteration\t' + str(self.collection_iteration))
        layout.label(text='element gesture_direction_items\t' + str(self.gesture_direction_items))
        layout.separator()
        for i in self.bl_rna.properties.keys():
            if i not in ('rna_type', 'name', 'relationship', "poll_string"):
                row = layout.row()
                row.label(text=i)
                row.prop(self, i, expand=True)

    def draw_alert(self, layout):
        """绘制警告信息
        如果元素有错误将会显示"""
        from .element_relationship import get_available_selected_structure
        alert_list = []
        if self.is_selected_structure:
            if not self.__poll_bool_is_validity__:
                alert_list.append(f'{pgettext_iface("Condition error")}: {self.poll_string}')
                alert_list.append(self.__poll_exception_info__)
            if not get_available_selected_structure(self):
                alert_list.append('Wrong choice of structure')
                alert_list.append('Previous element may not be a selection structure')
                alert_list.append('Or an expression error in the previous structure')
                if self.is_selected_elif:
                    alert_list.append('The previous selection structure of elif needs to be either if or elif.')
                elif self.is_selected_else:
                    alert_list.append('The previous selection structure of else needs to be an if or elif.')
                else:
                    alert_list.append("I don't know what's wrong there either :>")
                    alert_list.append("Maybe it's not enabled")
        elif self.is_operator:
            if self.operator_type == "OPERATOR":
                if not self.__operator_id_name_is_validity__:
                    alert_list.append(f'Operator Error')
                    alert_list.append(f'{pgettext_iface("Not find operator")}: {self.operator_bl_idname}')
                if not self.__operator_properties_is_validity__:
                    alert_list.append(f'{pgettext_iface("Operator property error")}: {self.operator_properties}')
        if alert_list:
            col = layout.box().column(align=True)
            col.alert = True
            col.label(text='Warning', icon='ERROR')
            for alert in alert_list:
                col.label(text=alert)

    def draw_icon(self, layout):
        if self.draw_property.element_show_icon:
            if self.is_draw_context_toggle_operator_bool:
                layout.label(text='', icon='BLANK1')
            elif self.is_draw_icon:
                layout.label(text='', icon_value=self.__get_icon__(self.icon))
            else:
                layout.label(text='', icon='BLANK1')

    def draw_edit_icon(self, layout):
        from ..ops.select_icon import SelectIcon
        if self.is_draw_context_toggle_operator_bool:
            layout.label(text="Use property toggle icon")
        else:
            row = layout.row(align=True)
            row.prop(self, 'enabled_icon')
            if self.icon_is_validity:
                row.prop(self, 'icon', text='', icon_value=self.__get_icon__(self.icon))
            else:
                row.alert = True
                row.prop(self, 'icon', text='', icon='ERROR')
            row.operator(SelectIcon.bl_idname, text='', icon='RESTRICT_SELECT_OFF')

    def draw_operator(self, layout):
        is_operator = self.operator_type == 'OPERATOR'
        is_modal = self.operator_type == "MODAL"
        is_script = self.operator_type == "SCRIPT"

        preview_script = self.preview_operator_script
        row = layout.row(align=True)
        col = row.column(align=True)
        col.prop(self, 'name')
        self.draw_edit_icon(col)
        col.prop(self, 'operator_type')

        if is_operator or is_modal:
            c = col.column(align=True)
            c.alert = not self.__operator_id_name_is_validity__
            c.prop(self, 'operator_bl_idname')
            b = col.column(align=True)
            b.alert = not self.__operator_properties_is_validity__
            b.prop(self, 'operator_properties')
        elif is_script:
            c = col.column(align=True)
            c.operator(ElementCURE.ScriptEdit.bl_idname)
            rr = c.row(align=True)
            rr.label(text=f'{pgettext_iface("Script word count")}:{len(self.operator_script)}')
            rr.separator()
            rr.prop(self, 'preview_operator_script', icon=icon_two(preview_script, style="HIDE"), text='',
                    emboss=False)

        if not self.parent_is_extension:  # 如果是展开菜单就不显示方向设置
            SetDirection.draw_direction(row.column())

        if is_operator or is_modal:
            is_change = self.properties != self.operator_tmp_kmi_properties
            row = layout.row(align=True)
            row.prop(self, 'operator_context')
            row.alert = is_change
            row.prop(self.other_property, 'auto_update_element_operator_properties', icon='FILE_REFRESH', text='')
            row.prop(self, 'operator_properties_sync_from_temp_properties', icon='SORT_DESC')
            row.prop(self, 'operator_properties_sync_to_properties', icon='SORT_ASC')
            if self.other_property.auto_update_element_operator_properties:
                self.from_tmp_kmi_operator_update_properties()

            layout.box().template_keymap_item_properties(self.operator_tmp_kmi)
            if is_change:
                layout.alert = True
                layout.label(text='Properties have changed, please synchronize or turn on the auto update button.',
                             icon='ERROR')
                layout.alert = False
            if is_modal:
                self.draw_operator_modal(layout)
        elif is_script:
            if preview_script:
                script_box = layout.box()
                for i in self.operator_script.split('\n'):
                    script_box.label(text=i)

    def draw_operator_modal(self, layout):
        from .element_modal_operator_cure import ElementModalOperatorEventCRUE
        from ..ui.ui_list import ElementModalEventUIList

        box = layout.box()
        box.label(text='Modal event control')
        row = box.row(align=True)
        row.template_list(
            ElementModalEventUIList.bl_idname,
            ElementModalEventUIList.bl_idname,
            self,
            'modal_events',
            self,
            'modal_events_index',
        )
        col = row.column(align=True)
        col.operator(ElementModalOperatorEventCRUE.ADD.bl_idname, text="", icon="ADD")
        col.operator(ElementModalOperatorEventCRUE.REMOVE.bl_idname, text="", icon="REMOVE")
