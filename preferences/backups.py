import json
import os

import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty

from ..utils.backups import (
    get_default_backups_folder,
    get_preferences_backup_path,
    log_backup,
    resolve_backups_folder,
    resolve_preferences_backup_path,
)
from ..utils.property import set_property, get_property


class BackupsProperty(bpy.types.PropertyGroup):
    auto_backups: BoolProperty(
        name='Enable auto backups',
        description=(
            'Automatically export gesture data when the add-on is disabled or Blender closes. '
            'Preference settings are always saved separately on disable.'
        ),
        default=True,
    )
    backup_on_blender_close: BoolProperty(
        name='Backup when Blender closes',
        description='Export gesture data every time Blender exits',
        default=True,
    )
    backup_on_disable_addon: BoolProperty(
        name='Backup when disabling add-on',
        description='Export gesture data when the add-on is disabled without closing Blender',
        default=True,
    )
    enabled_backups_to_specified_path: BoolProperty(
        name='Use custom backup folder',
        description='Save gesture backups to a custom folder instead of the default',
        default=False,
    )
    backups_path: StringProperty(
        name='Custom backup folder',
        description='Folder for gesture JSON backups when custom path is enabled',
        subtype='DIR_PATH',
        default="",
    )
    backups_file_mode: EnumProperty(
        name="Blender close backup mode",
        description='How to name backup files when Blender closes',
        default="BLENDER_CLOSE_EVERY",
        items=[
            ("BLENDER_CLOSE_EVERY", "Every close",
             "Create a new backup file each time Blender closes (filename includes date and time)"),
            ("BLENDER_CLOSE_DAY", "One per day",
             "Keep at most one backup file per day when Blender closes"),
            ("BLENDER_CLOSE_ONE", "Single file",
             "Overwrite one backup file on each Blender close"),
        ],
    )

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        from bpy.app.translations import pgettext_iface as translate
        from ..utils.public import get_pref

        pref = get_pref()
        backups = pref.backups_property
        column = layout.column(heading=translate("Auto Backups"))

        box = column.box()
        default_folder = get_default_backups_folder()
        active_folder = resolve_backups_folder()

        box.label(text=translate("Default backup folder:"))
        box.label(text=default_folder, translate=False)

        box.operator("wm.url_open", text=translate("Open Backup Folder")).url = active_folder
        box.prop(backups, 'auto_backups')
        if backups.auto_backups:
            box.prop(backups, 'backup_on_blender_close')
            if backups.backup_on_blender_close:
                box.prop(backups, 'backups_file_mode')
            box.prop(backups, 'backup_on_disable_addon')
        box.prop(backups, 'enabled_backups_to_specified_path')
        if backups.enabled_backups_to_specified_path:
            box.prop(backups, 'backups_path')

        if active_folder != default_folder:
            box.separator()
            box.label(text=translate("Active backup folder:"))
            box.label(text=active_folder, translate=False)


class BackupsPreferences:
    def preferences_backups(self, export_path=None):
        if not export_path:
            export_path = get_preferences_backup_path()
        log_backup(f"preferences start -> {export_path}")
        data = get_property(self, exclude=("gesture", "index_gesture", "name", "init_addon"))
        with open(export_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=True, indent=2))
        log_backup(f"preferences ok -> {export_path}")

    def preferences_restore(self, file_path=None):
        from ..utils.public import get_pref

        if not file_path:
            file_path = resolve_preferences_backup_path()
        if not file_path or not os.path.isfile(file_path):
            log_backup("preferences restore skipped: file not found")
            return
        log_backup(f"preferences restore <- {file_path}")
        from ..utils.selection import suppress_radio_updates

        with open(file_path, "r", encoding="utf-8") as file:
            with suppress_radio_updates():
                set_property(get_pref(), json.loads(file.read()))
        log_backup("preferences restore ok")
