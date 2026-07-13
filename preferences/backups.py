import json
import os

import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty

from ..utils.backups import (
    get_default_backups_folder,
    get_preferences_backup_path,
    load_preferences_backup_file,
    log_backup,
    resolve_backups_folder,
    resolve_preferences_backup_path,
)
from ..utils.property import set_property, get_property


class BackupsProperty(bpy.types.PropertyGroup):
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
    auto_restore_backups: BoolProperty(
        name='Auto restore backups',
        description=(
            'On enable, restore add-on preferences from the backup folder. '
            'Gesture data is loaded from the config JSON separately. '
            'Manual import is unaffected'
        ),
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
             "Create a new backup file each time Blender closes (filename includes date and time)\n"
             "Gesture Blender Close Backups YYYY-MM-DD-HH-MM-SS.json"),
            ("BLENDER_CLOSE_DAY", "One per day",
             "Keep at most one backup file per day when Blender closes\n"
             "Gesture Blender Close Backups YYYY-MM-DD.json"),
            ("BLENDER_CLOSE_ONE", "Single file",
             "Overwrite one backup file on each Blender close\n"
             "Gesture Blender Close Backups.json"),
        ],
    )

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        from bpy.app.translations import pgettext_iface as translate
        from ..utils.public import get_pref

        pref = get_pref()
        backups = pref.backups_property
        column = layout.column(heading=translate("Auto Backups"), align=True)

        box = column.box()
        default_folder = get_default_backups_folder()
        active_folder = resolve_backups_folder()

        row = box.row(align=True)
        row.prop(backups, 'backup_on_blender_close')
        sub = row.row(align=True)
        sub.enabled = backups.backup_on_blender_close
        sub.prop(backups, 'backups_file_mode', text="")
        box.prop(backups, 'backup_on_disable_addon')
        box.prop(backups, 'auto_restore_backups')

        box.separator()
        box.label(text=translate(
            "Preferences are always backed up on disable or exit"
        ))
        box.label(text=translate(
            "Gestures are saved under the extension user folder "
            "(legacy Blender config is still loaded if present)"
        ))

        from ..utils.backups import resolve_gestures_save_path
        gesture_path = resolve_gestures_save_path()
        path_box = box.box()
        path_box.use_property_split = False
        path_box.label(text=translate("Gesture data file:"))
        path_row = path_box.row(align=True)
        path_row.label(text=gesture_path, translate=False)
        folder = os.path.dirname(gesture_path) if gesture_path else active_folder
        path_row.operator("wm.path_open", text="", icon='FILE_FOLDER').filepath = folder

        folder_box = box.box()
        folder_box.use_property_split = False
        folder_box.label(text=translate("Default backup folder:"))
        folder_box_row = folder_box.row(align=True)
        folder_box_row.label(text=default_folder, translate=False)
        folder_box_row.operator("wm.path_open", text="", icon='FILE_FOLDER').filepath = active_folder

        folder_box.prop(backups, 'enabled_backups_to_specified_path')
        if backups.enabled_backups_to_specified_path:
            folder_box.prop(backups, 'backups_path')

        if active_folder != default_folder:
            folder_box.separator()
            folder_box.label(text=translate("Active backup folder:"))
            folder_box.label(text=active_folder, translate=False)


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

        auto_restore = file_path is None
        if auto_restore and not get_pref().backups_property.auto_restore_backups:
            log_backup("preferences restore skipped: auto_restore_backups is disabled")
            return

        if auto_restore:
            file_path = resolve_preferences_backup_path()
        else:
            file_path = file_path.strip()
            if not file_path:
                raise ValueError("Please select a preferences backup file")

        if not file_path or not os.path.isfile(file_path):
            if auto_restore:
                log_backup("preferences restore skipped: file not found")
                return
            raise ValueError("Preferences backup file not found")

        try:
            data = load_preferences_backup_file(file_path)
        except ValueError as e:
            log_backup(f"preferences restore failed: {e}")
            if auto_restore:
                return
            raise

        # Drop removed / non-preference fields from older backups.
        backups = data.get("backups_property")
        if isinstance(backups, dict):
            backups.pop("auto_backups", None)
        gesture_prop = data.get("gesture_property")
        if isinstance(gesture_prop, dict):
            gesture_prop.pop("pass_through_keymap_type", None)
        # Gestures live in CONFIG JSON; never merge from preference backups.
        data.pop("gesture", None)
        data.pop("index_gesture", None)

        log_backup(f"preferences restore <- {file_path}")
        from ..utils.selection import suppress_radio_updates

        with suppress_radio_updates():
            set_property(get_pref(), data)
        log_backup("preferences restore ok")
