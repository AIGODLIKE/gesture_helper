import bpy

from .draw_gesture import GestureDraw
from ..utils.public import get_pref
from ..utils.ui_draw_sync import (
    get_frozen_active_element,
    get_frozen_active_gesture,
    get_frozen_preview_state,
    panel_pause_state,
)


class PreferencesDraw(GestureDraw):

    @staticmethod
    def preferences_draw(layout: bpy.types.UILayout):
        """Draw preferences panel
        """
        pref = get_pref()
        context = bpy.context
        # Resolve the pause source once for this context.  The cached result
        # lets both freeze checks avoid another global gesture/modal scan.
        message, layout_frozen = panel_pause_state(context)
        column = layout.column(align=True)

        PreferencesDraw.draw_topbar(column, message)

        # Keep the preview row in the same place while paused so the page does
        # not jump. It follows the rest of the frozen surface and is disabled.
        if pref.show_page == 'GESTURE':
            preview_column = column.column(align=True)
            preview_column.enabled = not message
            if layout_frozen:
                preview_active, preview_scope = get_frozen_preview_state(context)
            else:
                preview_active = None
                preview_scope = None
            PreferencesDraw.draw_gesture_preview_button(
                preview_column,
                active_gesture=(
                    get_frozen_active_gesture(context)
                    if layout_frozen
                    else pref.active_gesture
                ),
                active_element=(
                    get_frozen_active_element(context)
                    if layout_frozen
                    else pref.active_element
                ),
                frozen=bool(message),
                preview_active=preview_active,
                preview_scope=preview_scope,
            )

        if message and not layout_frozen:
            # Foreign modals can redraw Preferences repeatedly. The title
            # already explains the pause; do not build either heavy page.
            return

        sub_column = column.column(align=True)
        # A live gesture freezes the whole preferences surface.  The enabled
        # preference only gates the Gesture page during normal editing; the
        # Property page remains available when the add-on itself is disabled.
        sub_column.enabled = (
            (pref.enabled if pref.is_show_gesture else True)
            and not layout_frozen
        )

        if draw_func := getattr(pref, f'draw_ui_{pref.show_page.lower()}', None):
            if pref.show_page == 'GESTURE':
                draw_func(
                    sub_column,
                    allow_frozen=layout_frozen,
                    draw_preview=False,
                )
            else:
                draw_func(sub_column)

    @staticmethod
    def draw_topbar(layout: 'bpy.types.UILayout', message):
        """Draw preferences header bar."""
        pref = get_pref()
        row = layout.row(align=True)
        row.enabled = not message
        rr = row.row(align=True)
        rr.operator_context = "EXEC_DEFAULT"
        rr.prop(pref, 'enabled', text="", emboss=True)
        rr.operator("wm.gesture_save_userpref", text="", icon="FILE_TICK")

        row.prop(pref, 'show_page', expand=True)
        if message:
            status = row.row(align=True)
            status.enabled = False
            status.label(text=message, icon="PAUSE")

    @staticmethod
    def draw_ui_property(layout):
        """
        Draw property section
        :param layout:
        :return:
        """
        from .. import preferences
        from ..ops.export_import import ExportPreferences, ImportPreferences
        from ..ops.select_icon import (
            OpenCustomIconFolder,
            RefreshIcons,
            ExportCustomIcons,
            ImportCustomIcons,
        )
        pref = get_pref()

        row = layout.row()
        row.use_property_split = True
        column = row.column(align=True)

        col = column.box().column(align=True)
        col.prop(pref.draw_property, "panel_enable")
        col.prop(pref.draw_property, "panel_name")
        col.prop(pref.draw_property, "force_show_panels_during_modal")
        col.prop(pref.draw_property, "author")
        col.prop(pref.draw_property, "enable_name_translation")
        col.operator_context = "INVOKE_DEFAULT"
        col.operator(ExportPreferences.bl_idname)
        col.operator(ImportPreferences.bl_idname)

        icon_box = column.box()
        icon_row = icon_box.row(align=True)
        icon_row.label(text="Custom Icons")
        icon_ops = icon_row.row(align=True)
        icon_ops.operator_context = "INVOKE_DEFAULT"
        icon_ops.operator(OpenCustomIconFolder.bl_idname, text="", icon="FILE_FOLDER")
        icon_ops.operator(RefreshIcons.bl_idname, text="", icon="FILE_REFRESH")
        icon_ops.operator(ExportCustomIcons.bl_idname, text="", icon="EXPORT")
        icon_ops.operator(ImportCustomIcons.bl_idname, text="", icon="IMPORT")
        icon_box.label(
            text="Put PNG files in the custom icons folder to use them as gesture element icons"
        )

        column.separator()
        preferences.BackupsProperty.draw_backups(column)
        column.separator()
        preferences.DebugProperty.draw_debug(column)

        col = row.box().column(align=True)
        col.label(text='Gesture')
        preferences.GestureProperty.draw_gesture_property(col)
        col.separator()
        preferences.DrawProperty.draw_text_property(col)
        preferences.DrawProperty.draw_color_property(col)
