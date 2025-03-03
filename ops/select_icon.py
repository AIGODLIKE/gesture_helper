"""
https://extensions.blender.org/add-ons/icon-viewer/
"""
import math
import os

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator

from ..utils.public import get_pref, PublicProperty, ADDON_FOLDER

CUSTOM_ICON_FOLDER = os.path.join(ADDON_FOLDER, 'src', 'icon', 'custom')

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


class SelectIcon(Operator, PublicProperty):
    bl_idname = 'gesture.select_icon'
    bl_label = 'Select Icon'
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
        return get_pref().active_element is not None

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
        row.operator('wm.url_open', text='Open Custom Folder', icon='FILE_FOLDER').url = CUSTOM_ICON_FOLDER
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

        ics = bpy.types.UILayout.bl_rna.functions[
            "prop"].parameters["icon"].enum_items.keys()

        def get_icon_args(icon_name) -> dict:
            from ..utils.icons import check_icon

            if icon_name in ics and icons is None:  # 先看看有没有在Blender自带的库里面
                return {"icon": icon_name}
            elif check_icon(icon_name):
                icon_value = self.__get_icon__(key=icon_name)
                return {"icon_value": icon_value}
            else:  # Error 此图标不存在
                ...
                return {}

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


class RefreshIcons(Operator):
    bl_idname = "gesture.refresh_icons"
    bl_label = "Refresh Icons"

    def execute(self, context):
        from ..utils.icons import Icons
        Icons.reload_icons()
        return {'FINISHED'}


class ClearHistory(Operator):
    bl_idname = "gesture.clear_icons_history"
    bl_label = "Clear History"

    def execute(self, context):
        HISTORY.clear()
        return {'FINISHED'}
