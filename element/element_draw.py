# Gesture drawing
# Preview drawing
import bpy
from bpy.app.translations import pgettext_iface

from ..ops.set_direction import SetDirection
from ..utils.public import get_pref
from ..utils.public_ui import icon_two


class ElementDraw:
    def draw_name(self, layout: 'bpy.types.UILayout') -> None:
        """Draw the element name and a source-sync button when available."""
        from ..ops.select_icon import SyncElementName

        row = layout.row(align=True)
        row.prop(self, 'name')
        if self.can_sync_name:
            row.context_pointer_set('gesture_name_element', self)
            row.operator(SyncElementName.bl_idname, text='', icon='FILE_REFRESH')

    def draw_overlay_offset(self, layout: 'bpy.types.UILayout') -> None:
        # Offsets are a radial root-placement setting.  Keep the persisted RNA
        # field for backwards-compatible imports, but do not expose a control
        # for menu rows or nested panel elements where it has no effect.
        gesture = self.parent_gesture
        if not self.is_root or gesture is None or getattr(gesture, 'gesture_type', 'RADIAL') != 'RADIAL':
            return
        layout.prop(self, 'overlay_offset', text='Draw Offset')

    def draw_item(self, layout: 'bpy.types.UILayout', *, _active_element=None):
        pref = get_pref()
        draw = pref.draw_property
        active = _active_element if _active_element is not None else pref.active_element

        layout.context_pointer_set('move_element', self)
        layout.context_pointer_set('cut_element', self)

        column = layout.column(align=True)
        item_row = column.row(align=True)

        status_info = self.list_status_info
        leading = item_row.row(align=True)
        leading.ui_units_x = 2.0 + (
            1.0 if draw.element_show_enabled_button else 0.0
        )
        self.draw_item_left(leading, pref)

        name = item_row.row(align=True)
        name.alignment = 'LEFT'

        controls = item_row.row(align=True)
        controls.alignment = 'RIGHT'
        controls.ui_units_x = 4.75 + (
            1.0 if draw.element_show_icon else 0.0
        )
        if pref.__is_move_element__ or pref.__is_cut_element__:
            controls.ui_units_x += 1.0

        self.draw_item_right(
            name,
            controls,
            status_info=status_info,
            show_icon=draw.element_show_icon,
        )

        if pref.__is_move_element__:
            from .element_cure import ElementCURE
            r = controls.row(align=True)
            r.ui_units_x = 1.0
            r.active = r.enabled = self.is_movable
            r.operator(ElementCURE.MOVE.bl_idname, text="", icon="UV_SYNC_SELECT", emboss=False)
        elif pref.__is_cut_element__:
            from .element_cure import ElementCURE
            r = controls.row(align=True)
            r.ui_units_x = 1.0
            r.active = r.enabled = self.is_can_be_cut
            r.operator(ElementCURE.CUT.bl_idname, text="", icon="PASTEFLIPDOWN", emboss=False)
        self.draw_item_child(column, active)

    def draw_item_left(self, layout: 'bpy.types.UILayout', pref=None):
        from ..utils.icons import ui_icon
        if pref is None:
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
        elif self.is_property_display:
            row.label(text='', icon=ui_icon('PROPERTIES'))
        elif self.is_row:
            row.label(text='', icon=ui_icon('ARROW_LEFTRIGHT'))
        elif self.is_column:
            row.label(text='', icon=ui_icon('ALIGN_JUSTIFY'))
        elif self.is_box:
            row.label(text='', icon=ui_icon('MENU_PANEL'))
        else:
            row.label(text='', icon='BLANK1')

        in_panel = self.parent_is_extension or self.parent_is_layout
        if in_panel:  # Panel children: hide direction icon
            if self.is_child_gesture:
                row.label(text='', icon_value=pref.__get_icon__("MENU_PANEL"))
            else:
                row.label(text='', icon='BLANK1')
        elif (
                self.is_child_gesture or self.is_operator
                or self.is_property_display or self.is_layout_container
        ):
            row.label(text='', icon_value=pref.__get_icon__(self.direction))
        else:
            row.label(text='', icon='BLANK1')

    def draw_item_right(
            self,
            name_layout: 'bpy.types.UILayout',
            controls: 'bpy.types.UILayout',
            *,
            status_info=None,
            show_icon=True,
    ):
        name_layout.label(text=self.name_translate, translate=False)

        if status_info is None:
            status_info = self.list_status_info
        status_row = controls.row(align=True)
        status_row.ui_units_x = 2.75
        if not status_info.is_valid:
            status_row.alert = status_info.status.is_error
            status_icon = {
                'POLL_BLOCKED': 'LOCKED',
                'READ_ONLY_PROPERTY': 'LOCKED',
                'DISABLED': 'HIDE_OFF',
            }.get(status_info.status.name, 'ERROR')
            status_row.label(text=status_info.badge, icon=status_icon)
        else:
            status_row.label(text='')

        child_row = controls.row(align=True)
        child_row.ui_units_x = 1.0
        if len(self.element):
            child_row.prop(
                self,
                'show_child',
                text='',
                icon=icon_two(self.show_child, 'TRI'),
                emboss=False,
            )
        else:
            child_row.label(text='', icon='BLANK1')

        if show_icon:
            icon_row = controls.row(align=True)
            icon_row.ui_units_x = 1.0
            self.draw_icon(icon_row, reserve_space=True)

        select_row = controls.row(align=True)
        select_row.ui_units_x = 1.0
        select_row.prop(
            self,
            'radio',
            text='',
            icon=icon_two(self.radio, 'RESTRICT_SELECT'),
            emboss=False,
        )

    def draw_item_child(self, layout, active_element=None):
        if self.show_child and len(self.element):
            child = layout.box().column(align=True)
            child.enabled = self.enabled
            for element in self.element:
                element.draw_item(child, _active_element=active_element)
            child.separator()

    def draw_item_property(self, layout: 'bpy.types.UILayout', *, include_modal: bool = True) -> None:
        if self.is_selected_structure:
            from ..ops.set_poll import SetPollExpression
            icon = self.pref.__get_icon__(self.selected_type)

            layout.prop(self, 'name')

            row = layout.row()
            row.label(text='Structure element', icon_value=icon)
            row.operator_context = "INVOKE_DEFAULT"
            row.operator(SetPollExpression.bl_idname, icon='FILTER')
            layout.prop(self, 'poll_string')
            row = layout.row(align=True)
            row.prop(self, 'selected_type', expand=True)
        elif self.is_operator:
            self.draw_operator(layout)
            if include_modal and self.operator_is_modal:
                self.draw_operator_modal(layout)
        elif self.is_child_gesture:
            row = layout.row(align=True)
            column = row.column()
            self.draw_name(column)
            self.draw_edit_icon(column)
            column.label(text='Child gesture', icon_value=self.pref.__get_icon__(self.direction))

            # Extension / layout panel children share the parent's slot — no direction.
            if not (self.parent_is_extension or self.parent_is_layout):
                SetDirection.draw_direction(row.column())
            self.draw_overlay_offset(layout)
        elif self.is_property_display:
            self.draw_property_display(layout)
        elif self.is_layout_container:
            self.draw_layout_container(layout)

    def draw_property_display(self, layout: 'bpy.types.UILayout') -> None:
        row = layout.row(align=True)
        column = row.column()
        self.draw_name(column)
        path_col = column.column(align=True)
        path_col.alert = not self.__property_path_is_validity__
        path_col.prop(self, 'property_data_path')
        if self.__property_path_is_validity__:
            column.label(text=self.display_property_text, translate=False)
        else:
            alert = column.column(align=True)
            alert.alert = True
            alert.label(text='Property path not found', icon='ERROR')
        if not (self.parent_is_extension or self.parent_is_layout):
            SetDirection.draw_direction(row.column())

        advanced_header = layout.row(align=True)
        advanced_header.prop(
            self,
            'show_property_advanced',
            text='Property Settings',
            icon='TRIA_DOWN' if self.show_property_advanced else 'TRIA_RIGHT',
            emboss=False,
        )
        if self.show_property_advanced:
            advanced = layout.column(align=True)
            advanced.prop(self, 'property_show_value')
            if self.property_show_value:
                advanced.prop(self, 'property_value_format')

            prop_type = self.display_property_type
            if prop_type in {'INT', 'FLOAT'}:
                drag = advanced.row(align=True)
                drag.prop(self, 'property_drag_mode', text='')
                drag.prop(self, 'property_drag_invert', text='', icon='ARROW_LEFTRIGHT')
                if prop_type == 'FLOAT' and self.property_show_value:
                    advanced.prop(self, 'property_value_precision')
            elif prop_type == 'BOOLEAN':
                labels = advanced.row(align=True)
                labels.prop(self, 'property_true_text')
                labels.prop(self, 'property_false_text')
                advanced.prop(self, 'property_bool_icons_enabled')
                if self.property_bool_icons_enabled:
                    self.draw_property_state_icons(advanced)

        self.draw_overlay_offset(layout)
        self.draw_main_action(layout)

    def draw_property_state_icons(self, layout: 'bpy.types.UILayout') -> None:
        from ..ops.select_icon import SelectIcon
        from ..utils.icons import icon_layout_kwargs

        layout.context_pointer_set('gesture_icon_element', self)
        row = layout.row(align=True)
        for prop_name, target, label in (
                ('property_true_icon', 'PROPERTY_TRUE', 'On'),
                ('property_false_icon', 'PROPERTY_FALSE', 'Off')):
            icon = getattr(self, prop_name)
            cell = row.row(align=True)
            cell.prop(self, prop_name, text=label, **icon_layout_kwargs(icon))
            operator = cell.operator(SelectIcon.bl_idname, text='', icon='RESTRICT_SELECT_OFF')
            operator.target = target

    def draw_layout_container(self, layout: 'bpy.types.UILayout') -> None:
        from ..element.element_cure import ElementCURE
        from ..utils.enum import ENUM_LAYOUT_TYPE
        row = layout.row(align=True)
        column = row.column(align=True)
        self.draw_name(column)

        type_row = column.row(align=True)
        for identifier, label, _description in ENUM_LAYOUT_TYPE:
            operator = type_row.operator(
                ElementCURE.SwitchLayoutType.bl_idname,
                text=label,
                depress=self.element_type == identifier,
            )
            operator.layout_type = identifier

        alignment = column.row(align=True)
        alignment.label(text='Alignment')
        alignment.prop(self, 'layout_alignment', text='')

        actions = [
            item for item in self.panel_leaf_items
            if item.is_operator or item.is_property_display
        ]
        if actions:
            column.separator()
            column.label(text='Gesture Action')
            action_column = column.column(align=True)
            effective = self.main_element
            for item in actions:
                action_column.prop(
                    item,
                    'main_item',
                    text=item.name_translate,
                    icon='RADIOBUT_ON' if item == effective else 'RADIOBUT_OFF',
                    toggle=True,
                )

        advanced_header = column.row(align=True)
        advanced_header.prop(
            self,
            'show_layout_advanced',
            text='Advanced',
            icon='TRIA_DOWN' if self.show_layout_advanced else 'TRIA_RIGHT',
            emboss=False,
        )
        if self.show_layout_advanced:
            advanced = column.column(align=True)
            advanced.prop(self, 'layout_scale')

        self.draw_overlay_offset(column)

        if not self.element:
            column.label(text='No child items. Please add some.', icon='INFO')
        if not (self.parent_is_extension or self.parent_is_layout):
            SetDirection.draw_direction(row.column())

    def draw_main_action(self, layout: 'bpy.types.UILayout') -> None:
        """Draw the primary-action toggle for executable layout leaves."""
        if not (self.is_operator or self.is_property_display):
            return
        owner = self.main_action_layout
        if owner is None:
            return
        row = layout.row(align=True)
        row.prop(
            self,
            'main_item',
            text='Gesture Action',
            icon='RADIOBUT_ON' if owner.main_element == self else 'RADIOBUT_OFF',
            toggle=True,
        )

    def draw_debug(self, layout):
        """Draw debug info for this element."""
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
        """Draw warning info when the element has errors."""
        from .element_relationship import get_available_selected_structure
        from .element_status import ElementStatus, get_element_status_info

        alert_list = []
        if self.is_selected_structure:
            if not self.__poll_bool_is_validity__:
                alert_list.append(f'{pgettext_iface("Condition error")}: {self.poll_string}')
                alert_list.append(self.__poll_exception_info__)
            if not get_available_selected_structure(self):
                alert_list.append('Invalid structure selection')
                alert_list.append('The previous element may not be a conditional structure')
                alert_list.append('There may be an expression error in the previous structure item')
                if self.is_selected_elif:
                    alert_list.append('elif must follow if or elif')
                elif self.is_selected_else:
                    alert_list.append('else must follow if or elif')
                else:
                    alert_list.append("Could not determine why this structure item is invalid.")
                    alert_list.append("Check that the previous structure item is enabled.")
        elif self.is_operator:
            status_info = get_element_status_info(self, include_poll=True)
            if status_info.status is ElementStatus.INVALID_OPERATOR:
                alert_list.extend((
                    'Operator unavailable',
                    status_info.message or f'Operator not found: {self.operator_bl_idname}',
                ))
            elif status_info.status is ElementStatus.INVALID_ARGUMENTS:
                alert_list.extend((
                    'Invalid operator arguments',
                    status_info.message or 'The configured values do not match the operator RNA.',
                ))
            elif status_info.status is ElementStatus.POLL_BLOCKED:
                alert_list.extend((
                    'Unavailable in this context',
                    f'{self.operator_bl_idname}: {status_info.message}',
                ))
        elif self.is_property_display:
            status_info = get_element_status_info(self, include_poll=True)
            if status_info.status is ElementStatus.INVALID_PROPERTY:
                alert_list.extend((
                    'Invalid property path',
                    status_info.message or f'Property path not found: {self.property_data_path}',
                ))
            elif status_info.status is ElementStatus.READ_ONLY_PROPERTY:
                alert_list.extend((
                    'Property is read-only',
                    status_info.message or self.property_data_path,
                ))
        if alert_list:
            col = layout.box().column(align=True)
            status = get_element_status_info(self, include_poll=True).status
            col.alert = status.is_error
            col.label(text='Warning', icon='ERROR' if status.is_error else 'INFO')
            for alert in alert_list:
                col.label(text=alert)

    def draw_icon(self, layout, *, reserve_space=False):
        from ..utils.icons import icon_layout_kwargs
        if not self.draw_property.element_show_icon:
            return
        if not self.is_draw_context_toggle_operator_bool and self.is_draw_icon:
            layout.label(text='', **icon_layout_kwargs(self.icon))
        elif reserve_space:
            layout.label(text='', icon='BLANK1')

    def draw_edit_icon(self, layout):
        from ..ops.select_icon import SelectIcon
        from ..utils.icons import icon_layout_kwargs
        if self.is_draw_context_toggle_operator_bool:
            layout.label(text="Uses the property toggle icon")
        else:
            row = layout.row(align=True)
            row.prop(self, 'enabled_icon')
            if self.icon_is_validity:
                row.prop(self, 'icon', text='', **icon_layout_kwargs(self.icon))
            else:
                row.alert = True
                row.prop(self, 'icon', text='', icon='ERROR')
            row.operator(SelectIcon.bl_idname, text='', icon='RESTRICT_SELECT_OFF')

    def draw_operator(self, layout):
        from .element_status import ElementStatus, get_element_status_info

        is_operator = self.operator_type == 'OPERATOR'
        is_modal = self.operator_type == "MODAL"
        status_info = get_element_status_info(self, include_poll=False)

        row = layout.row(align=True)
        col = row.column(align=True)
        self.draw_name(col)
        self.draw_edit_icon(col)
        col.prop(self, 'operator_type')

        if is_operator or is_modal:
            c = col.column(align=True)
            c.alert = status_info.status is ElementStatus.INVALID_OPERATOR
            c.prop(self, 'operator_bl_idname')
            b = col.column(align=True)
            b.alert = status_info.status is ElementStatus.INVALID_ARGUMENTS
            b.prop(self, 'operator_properties')

        # Extension / layout panel children share the parent's slot — no direction.
        if not (self.parent_is_extension or self.parent_is_layout):
            SetDirection.draw_direction(row.column())

        if is_operator or is_modal:
            if self.other_property.auto_update_element_operator_properties:
                # Do not write RNA inside draw — debounce instead.
                from ..utils.ui_draw_sync import schedule

                def _flush():
                    from ..utils.public import get_pref
                    pref = get_pref()
                    active = pref.active_element
                    if (
                        active is not None
                        and active.is_operator
                        and pref.other_property.auto_update_element_operator_properties
                    ):
                        active.from_tmp_kmi_operator_update_properties()

                schedule('operator_tmp_kmi_sync', _flush)
            is_change = self.properties != self.operator_tmp_kmi_properties
            row = layout.row(align=True)
            row.prop(self, 'operator_context')
            row.alert = is_change
            row.prop(self.other_property, 'auto_update_element_operator_properties', icon='FILE_REFRESH', text='')
            row.prop(self, 'operator_properties_sync_from_temp_properties', icon='SORT_DESC')
            row.prop(self, 'operator_properties_sync_to_properties', icon='SORT_ASC')

            if is_modal:
                layout.prop(get_pref().gesture_property, "modal_pass_view_rotation")

            layout.box().template_keymap_item_properties(self.operator_tmp_kmi)
            if is_change:
                layout.alert = True
                layout.label(text='Properties have changed. Sync them or enable auto-update.',
                             icon='ERROR')
                layout.alert = False
            if is_modal:
                if self.is_not_recommended_as_modal:
                    column = layout.column(align=True)
                    column.alert = True
                    column.label(text='Not recommended as a modal operator', icon='ERROR')
                    column.label(text='This operator has array properties and cannot be mapped to modal events')

        self.draw_main_action(layout)
        self.draw_overlay_offset(layout)

    def draw_operator_modal(self, layout):
        from .element_modal_operator_cure import ElementModalOperatorEventCRUE
        from ..ui.ui_list import ElementModalEventUIList

        # Bind this element for modal ADD/COPY/REMOVE poll (create popup may
        # draw last_element while preferences selection is still elsewhere).
        layout.context_pointer_set('gesture_modal_element', self)

        column = layout.column(align=True)
        row = column.row(align=True)
        row.template_list(
            ElementModalEventUIList.bl_idname,
            ElementModalEventUIList.bl_idname,
            self,
            'modal_events',
            self,
            'modal_events_index',
        )
        col = row.column(align=True)
        # Preferences default to EXEC; confirm tips / modifier shortcuts need invoke.
        col.operator_context = "INVOKE_DEFAULT"
        col.operator(ElementModalOperatorEventCRUE.ADD.bl_idname, text="", icon="ADD")
        col.operator(ElementModalOperatorEventCRUE.COPY.bl_idname, text="", icon="COPYDOWN")
        col.operator(ElementModalOperatorEventCRUE.REMOVE.bl_idname, text="", icon="REMOVE")
        self.draw_modal_property(column)
