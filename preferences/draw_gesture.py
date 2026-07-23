import bpy

from .draw_element import DrawElement
from ..ops import export_import
from ..utils.public import get_pref


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
    def draw_gesture_key(layout) -> None:
        from ..utils.public import get_pref
        pref = get_pref()
        active = pref.active_gesture
        if active:
            column = layout.column()
            column.active = active.is_enable
            active.draw_key(column)
        else:
            layout.label(text=pref.__tn__('No gesture selected'))

    @staticmethod
    def draw_gesture_item(layout: bpy.types.UILayout) -> None:
        pref = get_pref()
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
        ag = pref.active_gesture
        if ag is not None:
            column.prop(ag, 'name')
            column.prop(ag, 'description')
            type_row = column.row(align=True)
            type_row.label(text='Type')
            type_row.label(
                text='Menu' if ag.gesture_type == 'MENU' else 'Gesture',
                icon='MENU_PANEL' if ag.gesture_type == 'MENU' else 'MOUSE_MOVE',
            )
            if ag.gesture_type == 'MENU':
                column.prop(ag, 'menu_style')
        GestureDraw.draw_gesture_key(column)

    @staticmethod
    def draw_element(layout: bpy.types.UILayout, *, include_modal: bool = True) -> None:
        from ..ui.ui_list import ElementUIList
        from ..utils.ui_draw_sync import draw_heavy_panel_paused, heavy_panel_skip_message

        # Same guard as GestureElementPanel: ElementUIList walks Element RNA that
        # the GPU overlay stamps with transient hit boxes; drawing mid-modal
        # churns Python proxies and wipes extension hover.
        msg = heavy_panel_skip_message(bpy.context)
        if msg:
            draw_heavy_panel_paused(layout, msg)
            return

        pref = get_pref()
        ag = pref.active_gesture
        if ag:
            column = layout.column()

            DrawElement.draw_element_add_property(column)
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
            DrawElement.draw_property(sub_column, include_modal=include_modal)

            DrawElement.draw_element_cure(row)
        else:
            layout.label(text='Add or select a gesture')

    @staticmethod
    def draw_ui_gesture(layout):
        """
        Draw gesture section
        :param layout:
        :return:
        """
        from ..utils.ui_draw_sync import draw_heavy_panel_paused, heavy_panel_skip_message

        pref = get_pref()
        draw_property = pref.draw_property
        active = pref.active_element

        # Left-side property editor also walks Element RNA — same modal wipe risk.
        msg = heavy_panel_skip_message(bpy.context)
        if msg:
            draw_heavy_panel_paused(layout, msg)
            return

        column = layout.column()
        split = column.split()

        if draw_property.element_show_left_side:  # Property panel on left
            box = split.box()
            box.operator_context = "INVOKE_DEFAULT"
            if active:
                active.draw_item_property(box)
            else:
                box.label(text='Add or select an element')
        else:
            GestureDraw.draw_gesture_item(split)
        GestureDraw.draw_element(split)

    @staticmethod
    def draw_gesture(layout: bpy.types.UILayout):
        pref = get_pref()
        act = pref.active_gesture
        if act:  # Property panel on left
            GestureDraw.draw_gesture_item(layout)
        else:
            layout.box().label(text='Add or select a gesture')

    @staticmethod
    def draw_gesture_preview_button(layout: bpy.types.UILayout) -> None:
        """Preview launcher for the 3D View panel (edit while previewing)."""
        from ..ops.quick_add.gesture_preview import GesturePreview
        from ..utils.session_state import SessionState
        from ..utils.icons import ui_icon

        pref = get_pref()
        ag = pref.active_gesture
        if ag is None or ag.gesture_type != 'RADIAL':
            return
        row = layout.row(align=True)
        row.enabled = pref.enabled
        if SessionState.gesture_preview_active:
            row.label(text="Previewing: edits show live; right-click the viewport to exit")
            return
        row.operator_context = "INVOKE_DEFAULT"
        ops = row.operator(
            GesturePreview.bl_idname,
            icon=ui_icon('HIDE_OFF'),
            text="Preview Gesture",
        )
        ops.gesture = ag.name
