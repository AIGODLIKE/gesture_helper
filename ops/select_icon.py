# Icon picker UI adapted from Icon Viewer (development_icon_get) by roaoao.
# SPDX-License-Identifier: GPL-2.0-or-later
# https://projects.blender.org/extensions/development_icon_get

import math
import os
import zipfile

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..utils.public import get_pref, PublicProperty, poll_message_active_element, poll_addon_preferences
from ..utils.icons import icon_layout_kwargs, CUSTOM_ICONS_EXPORT_FILENAME

DPI = 72
POPUP_PADDING = 10
PANEL_PADDING = 44
WIN_PADDING = 32
ICON_SIZE = 20
HISTORY_SIZE = 100
HISTORY = []


def ui_scale():
    prefs = bpy.context.preferences.system
    return prefs.dpi / DPI


def get_num_cols(num_icons):
    return round(1.3 * math.sqrt(num_icons))


class SelectIcon(bpy.types.Operator, PublicProperty):
    bl_idname = 'wm.gesture_select_icon'
    bl_label = 'Select Icon'
    bl_description = 'Pick a built-in Blender icon or a custom add-on icon for the active element'
    bl_options = {'REGISTER'}
    filtered_icons = []

    width: int

    def update_icons(self, context):
        SelectIcon.filtered_icons = []

        icon_filter = self.filter.upper()

        from ..utils.icons import get_blender_icons
        all_icons = get_blender_icons()
        for icon in all_icons:
            is_none = icon == 'NONE'
            is_filter = icon_filter and icon_filter not in icon
            is_brush = not self.show_brush_icons and "BRUSH_" in icon and icon != 'BRUSH_DATA'
            is_matcap = not self.show_matcap_icons and "MATCAP_" in icon
            is_event = not self.show_event_icons and ("EVENT_" in icon or "MOUSE_" in icon)
            is_color = not self.show_colorset_icons and "COLORSET_" in icon

            if is_none or is_filter or is_brush or is_matcap or is_event or is_color:
                continue
            SelectIcon.filtered_icons.append(icon)

    icon: StringProperty(options={"SKIP_SAVE"})

    filter: StringProperty(
        description="Filter",
        default="",
        update=update_icons,
        options={'TEXTEDIT_UPDATE', 'SKIP_SAVE'})
    show_history: BoolProperty(
        name="Show History",
        description="Show history", default=True)
    show_brush_icons: BoolProperty(
        name="Show Brush Icons",
        description="Show brush icons", default=True,
        update=update_icons)
    show_matcap_icons: BoolProperty(
        name="Show Matcap Icons",
        description="Show matcap icons", default=True,
        update=update_icons)
    show_event_icons: BoolProperty(
        name="Show Event Icons",
        description="Show event icons", default=True,
        update=update_icons)
    show_colorset_icons: BoolProperty(
        name="Show Colorset Icons",
        description="Show colorset icons", default=True,
        update=update_icons)
    copy_on_select: BoolProperty(
        name="Copy Icon On Click",
        description="Copy icon on click", default=True)

    @classmethod
    def poll(cls, context):
        return poll_message_active_element(cls)

    def invoke(self, context, event):
        self.update_icons(context)
        num_cols = get_num_cols(len(self.filtered_icons))

        self.width = width = int(min(
            ui_scale() * (num_cols * ICON_SIZE + POPUP_PADDING),
            context.window.width - WIN_PADDING))

        return context.window_manager.invoke_props_dialog(self, width=width)

    def execute(self, context):
        from ..utils.icons import check_icon
        if check_icon(self.icon):
            self.update_history()

            bpy.context.window_manager.clipboard = self.icon

            act = get_pref().active_element
            act.icon = self.icon
            act.enabled_icon = True
        return {'FINISHED'}

    def update_history(self):
        if self.icon in HISTORY:
            HISTORY.remove(self.icon)
        if len(HISTORY) >= HISTORY_SIZE:
            HISTORY.pop(0)
        HISTORY.append(self.icon)

    def draw(self, context):
        col = self.layout
        self.draw_header(col)

        history_num_cols = int((self.width - POPUP_PADDING) / (ui_scale() * ICON_SIZE))
        num_cols = max(min(get_num_cols(len(self.filtered_icons)), history_num_cols), 20)

        if HISTORY:
            hi = col.box().row(align=True)
            hi.alignment = 'CENTER'
            hi.label(text='History')
            self.draw_icons(hi.column(align=True), num_cols, icons=HISTORY)
            hi.operator(ClearHistory.bl_idname, icon='PANEL_CLOSE')

        from ..utils.icons import icons_map

        row = col.box().row()
        row.alignment = 'CENTER'
        row.label(text='Addon')
        self.draw_icons(row.column(align=True), num_cols, icons=icons_map.get('ADDON'))

        box = col.box()
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text='Custom')
        self.draw_icons(row.column(align=True), num_cols, icons=icons_map.get('CUSTOM'))

        row = box.row()
        row.separator()
        row.operator(RefreshIcons.bl_idname, icon='FILE_REFRESH')
        row.separator()
        row.operator(OpenCustomIconFolder.bl_idname, icon='FILE_FOLDER')
        row.separator()

        box = col.box()
        box.label(text='Blender')
        self.draw_icons(box.column(align=True), num_cols)

    def draw_header(self, layout):
        header = layout.box()
        header = header.row()
        row = header.row(align=True)
        row.prop(self, 'show_event_icons', text='', icon='HAND')
        row.separator()

        row.prop(
            self, 'copy_on_select', text='',
            icon='COPYDOWN', toggle=True)
        row.separator()

        row.prop(self, 'filter', text='', icon='VIEWZOOM')

    def draw_icons(self, layout, num_cols=0, icons=None):
        if icons is not None:
            filtered_icons = list(reversed(icons))
        else:
            filtered_icons = SelectIcon.filtered_icons

        column = layout.column(align=True)
        row = column.row(align=True)
        row.alignment = 'CENTER'
        row.operator_context = 'EXEC_DEFAULT'

        selected_icon = bpy.context.window_manager.clipboard
        col_idx = 0
        i: int = 0

        def get_icon_args(icon_name) -> dict:
            return icon_layout_kwargs(icon_name)

        for i, icon in enumerate(filtered_icons):
            args = get_icon_args(icon)
            p = row.operator(
                SelectIcon.bl_idname,
                text="",
                emboss=icon == selected_icon,
                **args,
            )
            p.icon = icon

            col_idx += 1
            if col_idx > num_cols - 1:
                # if icons:
                #     break
                col_idx = 0
                if i < len(filtered_icons) - 1:
                    row = column.row(align=True)
                    row.alignment = 'CENTER'
                    row.operator_context = 'EXEC_DEFAULT'

        if col_idx != 0 and not icons and i >= num_cols:
            for _ in range(num_cols - col_idx):
                row.label(text="", icon='BLANK1')

        if not filtered_icons:
            row.label(text="No icons were found")


class RefreshIcons(bpy.types.Operator):
    bl_idname = "wm.gesture_refresh_icons"
    bl_label = "Refresh Icons"
    bl_description = 'Reload custom add-on icon previews from disk'

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def execute(self, context):
        from ..utils.icons import Icons
        Icons.reload_icons()
        return {'FINISHED'}


class OpenCustomIconFolder(bpy.types.Operator):
    bl_idname = "wm.gesture_open_custom_icon_folder"
    bl_label = "Open Custom Folder"
    bl_description = "Open the custom icons folder; create it if missing"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def execute(self, context):
        from ..utils.icons import ensure_custom_icons_folder
        path = ensure_custom_icons_folder()
        bpy.ops.wm.path_open(filepath=path)
        return {'FINISHED'}


class ExportCustomIcons(bpy.types.Operator, ExportHelper):
    bl_idname = "wm.gesture_export_custom_icons"
    bl_label = "Export Custom Icons"
    bl_description = "Export custom icons from the user folder as a ZIP archive"

    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={'HIDDEN'}, maxlen=255)

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def invoke(self, context, event):
        from ..utils.backups import get_default_backups_folder
        if not (self.filepath or "").strip():
            self.filepath = os.path.join(get_default_backups_folder(), CUSTOM_ICONS_EXPORT_FILENAME)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from bpy.app.translations import pgettext
        from ..utils.icons import export_custom_icons_zip

        filepath = (self.filepath or "").strip()
        if not filepath:
            self.report({'ERROR'}, pgettext("Please select an export path"))
            return {'CANCELLED'}
        if not filepath.lower().endswith(".zip"):
            filepath = filepath + ".zip"
            self.filepath = filepath

        try:
            count = export_custom_icons_zip(filepath)
        except OSError:
            self.report({'ERROR'}, pgettext("Export error, please check path %s") % filepath)
            return {'CANCELLED'}

        if count == 0:
            self.report({'WARNING'}, pgettext("No custom icons to export"))
            return {'CANCELLED'}

        self.report({'INFO'}, pgettext("Exported %d custom icons") % count)
        return {'FINISHED'}


class ImportCustomIcons(bpy.types.Operator, ImportHelper):
    bl_idname = "wm.gesture_import_custom_icons"
    bl_label = "Import Custom Icons"
    bl_description = "Import custom icons from a ZIP archive into the user folder"

    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={'HIDDEN'}, maxlen=255)

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def invoke(self, context, event):
        from ..utils.backups import get_default_backups_folder
        self.filepath = os.path.join(get_default_backups_folder(), CUSTOM_ICONS_EXPORT_FILENAME)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from bpy.app.translations import pgettext
        from ..utils.icons import Icons, import_custom_icons_zip

        filepath = (self.filepath or "").strip()
        if not filepath:
            self.report({'ERROR'}, pgettext("Please select a custom icons ZIP file"))
            return {'CANCELLED'}
        if not os.path.isfile(filepath):
            self.report({'ERROR'}, pgettext("Please select a custom icons ZIP file"))
            return {'CANCELLED'}

        try:
            count = import_custom_icons_zip(filepath)
        except (OSError, zipfile.BadZipFile):
            self.report({'ERROR'}, pgettext("Import error, please select a valid ZIP file"))
            return {'CANCELLED'}

        if count == 0:
            self.report({'WARNING'}, pgettext("No PNG icons found in ZIP"))
            return {'CANCELLED'}

        Icons.reload_icons()
        self.report({'INFO'}, pgettext("Imported %d custom icons") % count)
        return {'FINISHED'}


class ClearHistory(bpy.types.Operator):
    bl_idname = "wm.gesture_clear_icons_history"
    bl_label = "Clear History"
    bl_description = 'Clear the icon selection history list'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return poll_message_active_element(cls)

    def execute(self, context):
        HISTORY.clear()
        return {'FINISHED'}
