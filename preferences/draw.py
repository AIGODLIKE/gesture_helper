import bpy

from .draw_gesture import GestureDraw
from ..utils.public import get_pref


class PreferencesDraw(GestureDraw):

    @staticmethod
    def preferences_draw(layout: bpy.types.UILayout):
        """Draw preferences panel
        """
        pref = get_pref()
        column = layout.column(align=True)

        PreferencesDraw.draw_topbar(column)

        sub_column = column.column(align=True)
        if pref.is_show_gesture:
            sub_column.enabled = pref.enabled

        if draw_func := getattr(pref, f'draw_ui_{pref.show_page.lower()}', None):
            draw_func(sub_column)

    @staticmethod
    def draw_topbar(layout: 'bpy.types.UILayout'):
        """Draw preferences header bar."""
        pref = get_pref()
        row = layout.row(align=True)
        rr = row.row(align=True)
        rr.operator_context = "EXEC_DEFAULT"
        rr.prop(pref, 'enabled', text="", emboss=True)
        rr.operator("wm.gesture_save_userpref", text="", icon="FILE_TICK")

        row.prop(pref, 'show_page', expand=True)

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
