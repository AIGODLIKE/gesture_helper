import bpy

from .draw_element import DrawElement
from ..ops import export_import
from ..utils.public import get_pref


_ACTIVE_ELEMENT_UNSET = object()
_ACTIVE_GESTURE_UNSET = object()


class GestureDraw:

    @staticmethod
    def draw_gesture_cure(layout: 'bpy.types.UILayout') -> None:
        from ..ops.gesture_cure import GestureCURE

        column = layout.column(align=True)
        # Preferences default to EXEC; confirm tips / modifier shortcuts need invoke.
        column.operator_context = "INVOKE_DEFAULT"

        column.operator(GestureCURE.ADD.bl_idname, icon='ADD', text='')
        column.operator(GestureCURE.COPY.bl_idname, text='', icon='COPYDOWN')
        column.operator(GestureCURE.REMOVE.bl_idname, text='', icon='REMOVE')

        column.separator()

        sort_column = column.column(align=True)
        sort_column.operator(GestureCURE.SORT.bl_idname, icon='SORT_DESC', text='').is_next = False

        sort_column.operator(GestureCURE.SORT.bl_idname, icon='SORT_ASC', text='').is_next = True

        column.separator()

        import_id_name = export_import.Import.bl_idname
        column.operator(export_import.Export.bl_idname, icon='EXPORT', text='')
        column.operator(import_id_name, icon='ASSET_MANAGER', text='').preset_show = True
        column.operator(import_id_name, icon='IMPORT', text='').preset_show = False

    @staticmethod
    def draw_gesture_key(
            layout,
            *,
            active_gesture=_ACTIVE_GESTURE_UNSET,
    ) -> None:
        from ..utils.public import get_pref
        pref = get_pref()
        active = (
            pref.active_gesture
            if active_gesture is _ACTIVE_GESTURE_UNSET
            else active_gesture
        )
        if active:
            column = layout.column()
            column.active = active.is_enable
            active.draw_key(column)
        else:
            layout.label(text=pref.__tn__('No gesture selected'))

    @staticmethod
    def draw_gesture_item(
            layout: bpy.types.UILayout,
            *,
            active_gesture=_ACTIVE_GESTURE_UNSET,
    ) -> None:
        pref = get_pref()
        active = (
            pref.active_gesture
            if active_gesture is _ACTIVE_GESTURE_UNSET
            else active_gesture
        )
        row = layout.row(align=True)
        row.enabled = row.active = not pref.__is_move_element__

        GestureDraw.draw_gesture_cure(row)
        column = row.column(align=True)
        from ..ui.ui_list import GestureUIList
        from ..utils.gesture_store import get_gesture_store
        store = get_gesture_store()
        if store is None:
            column.label(text="Gesture store unavailable")
            return
        column.template_list(
            GestureUIList.bl_idname,
            GestureUIList.bl_idname,
            store,
            'gesture',
            store,
            'index_gesture',
        )
        ag = active
        if ag is not None:
            column.prop(ag, 'name')
            column.prop(ag, 'description')
            type_row = column.row(align=True)
            type_row.label(text='Type')
            # Type selects a different runtime/keymap implementation.  Keep it
            # visible for clarity, but render it as ordinary read-only text so
            # it matches the surrounding rows rather than a disabled dropdown.
            from ..utils.icons import ui_icon

            is_menu = ag.gesture_type == 'MENU'
            type_row.label(
                text='Menu' if is_menu else 'Gesture',
                icon=ui_icon('MENU_PANEL' if is_menu else 'MOUSE_MOVE'),
            )
            if ag.gesture_type == 'MENU':
                type_row.prop(ag, 'menu_style', text='')
        GestureDraw.draw_gesture_key(column, active_gesture=active)

    @staticmethod
    def draw_element(
            layout: bpy.types.UILayout,
            *,
            include_modal: bool = True,
            allow_frozen: bool = False,
            active_element=_ACTIVE_ELEMENT_UNSET,
            active_gesture=_ACTIVE_GESTURE_UNSET,
    ) -> None:
        from ..ui.ui_list import ElementUIList
        from ..utils.ui_draw_sync import draw_heavy_panel_paused, heavy_panel_skip_message

        # Same guard as GestureElementPanel: ElementUIList walks Element RNA that
        # the GPU overlay stamps with transient hit boxes; drawing mid-modal
        # churns Python proxies and wipes extension hover.
        msg = None if allow_frozen else heavy_panel_skip_message(bpy.context)
        if msg and not allow_frozen:
            draw_heavy_panel_paused(layout, msg)
            return

        pref = get_pref()
        if allow_frozen:
            from ..utils.ui_draw_sync import (
                get_frozen_active_element,
                get_frozen_active_gesture,
            )
            if active_element is _ACTIVE_ELEMENT_UNSET:
                active_element = get_frozen_active_element(bpy.context)
            if active_gesture is _ACTIVE_GESTURE_UNSET:
                active_gesture = get_frozen_active_gesture(bpy.context)
        ag = (
            pref.active_gesture
            if active_gesture is _ACTIVE_GESTURE_UNSET
            else active_gesture
        )
        if ag:
            column = layout.column()

            DrawElement.draw_element_add_property(
                column,
                frozen=allow_frozen,
            )
            row = column.row(align=True)

            sub_column = row.column()
            sub_column.template_list(
                ElementUIList.bl_idname,
                ElementUIList.bl_idname,
                ag,
                'element',
                ag,
                'index_element',
            )
            if active_element is _ACTIVE_ELEMENT_UNSET:
                DrawElement.draw_property(
                    sub_column,
                    include_modal=include_modal,
                )
            else:
                DrawElement.draw_property(
                    sub_column,
                    include_modal=include_modal,
                    active_element=active_element,
                )

            DrawElement.draw_element_cure(row)
        else:
            layout.label(text='Add or select a gesture')

    @staticmethod
    def draw_ui_gesture(
            layout,
            *,
            allow_frozen: bool = False,
            draw_preview: bool = True,
    ):
        """
        Draw gesture section
        :param layout:
        :return:
        """
        from ..utils.ui_draw_sync import draw_heavy_panel_paused, heavy_panel_skip_message

        pref = get_pref()
        draw_property = pref.draw_property
        if allow_frozen:
            from ..utils.ui_draw_sync import (
                get_frozen_active_element,
                get_frozen_active_gesture,
            )
            active = get_frozen_active_element(bpy.context)
            active_gesture = get_frozen_active_gesture(bpy.context)
        else:
            active = pref.active_element
            active_gesture = _ACTIVE_GESTURE_UNSET

        # Left-side property editor also walks Element RNA — same modal wipe risk.
        msg = None if allow_frozen else heavy_panel_skip_message(bpy.context)
        if msg and not allow_frozen:
            draw_heavy_panel_paused(layout, msg)
            return

        column = layout.column()
        if draw_preview:
            GestureDraw.draw_gesture_preview_button(
                column,
                active_gesture=active_gesture,
            )
        split = column.split()

        if draw_property.element_show_left_side:  # Property panel on left
            box = split.box()
            box.operator_context = "INVOKE_DEFAULT"
            if active:
                active.draw_alert(box)
                active.draw_item_property(box)
            else:
                box.label(text='Add or select an element')
        else:
            GestureDraw.draw_gesture_item(
                split,
                active_gesture=active_gesture,
            )
        GestureDraw.draw_element(
            split,
            allow_frozen=allow_frozen,
            active_element=(active if allow_frozen else _ACTIVE_ELEMENT_UNSET),
            active_gesture=active_gesture,
        )

    @staticmethod
    def draw_gesture(
            layout: bpy.types.UILayout,
            *,
            active_gesture=_ACTIVE_GESTURE_UNSET,
    ):
        pref = get_pref()
        act = (
            pref.active_gesture
            if active_gesture is _ACTIVE_GESTURE_UNSET
            else active_gesture
        )
        if act:  # Property panel on left
            GestureDraw.draw_gesture_item(layout, active_gesture=act)
        else:
            layout.box().label(text='Add or select a gesture')

    @staticmethod
    def draw_gesture_preview_button(
            layout: bpy.types.UILayout,
            *,
            active_gesture=_ACTIVE_GESTURE_UNSET,
            active_element=_ACTIVE_ELEMENT_UNSET,
            frozen: bool = False,
            preview_active: bool | None = None,
            preview_scope: str | None = None,
    ) -> None:
        """Preview launcher for the 3D View panel (edit while previewing)."""
        from ..ops.quick_add.gesture_preview import (
            GesturePreview,
            GesturePreviewClose,
            GesturePreviewFrozen,
        )
        from ..utils.session_state import SessionState
        from ..utils.icons import ui_icon

        row = layout.row(align=True)
        if preview_active is None:
            preview_active = bool(SessionState.gesture_preview_active)
        if preview_scope is None:
            preview_scope = str(SessionState.gesture_preview_scope or '')
        if preview_active:
            label = (
                'Previewing Element'
                if preview_scope == 'ELEMENT'
                else 'Previewing Gesture'
            )
            row.label(text=label, icon=ui_icon('HIDE_OFF'))
            row.operator(
                (
                    GesturePreviewFrozen.bl_idname
                    if frozen
                    else GesturePreviewClose.bl_idname
                ),
                text='Close Preview',
                icon='X',
            )
            return

        pref = get_pref()
        ag = (
            pref.active_gesture
            if active_gesture is _ACTIVE_GESTURE_UNSET
            else active_gesture
        )
        ae = (
            pref.active_element
            if active_element is _ACTIVE_ELEMENT_UNSET
            else active_element
        )
        if ag is None:
            return
        row.operator_context = "INVOKE_DEFAULT"
        gesture_button = row.row(align=True)
        gesture_button.enabled = pref.enabled
        preview_operator = GesturePreviewFrozen if frozen else GesturePreview
        ops = gesture_button.operator(
            preview_operator.bl_idname,
            icon=ui_icon('HIDE_OFF'),
            text="Preview Gesture",
        )
        if not frozen:
            ops.gesture = ag.name
            ops.scope = 'GESTURE'

        element_button = row.row(align=True)
        element_button.enabled = pref.enabled and ae is not None
        ops = element_button.operator(
            preview_operator.bl_idname,
            icon='ZOOM_IN',
            text='Preview Element',
        )
        if not frozen:
            ops.gesture = ag.name
            ops.scope = 'ELEMENT'
