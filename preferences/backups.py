import json
import os

import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty

from ..utils.property import set_property, get_property


class BackupsProperty(bpy.types.PropertyGroup):
    auto_backups: BoolProperty(
        name='Enable auto backups',
        description='Automatically save gesture data when the add-on is disabled or Blender closes. Default folder is the extension user data directory.',
        default=True,
    )
    enabled_backups_to_specified_path: BoolProperty(
        name='Specify the backup path',
        description='Backup files are saved to a specified path',
        default=False,
    )
    backups_path: StringProperty(
        name='Backup path',
        description='Backup Configuration to a Specified Path',
        subtype='DIR_PATH',
        default="",
    )
    backups_file_mode: EnumProperty(
        name="Backup mode",
        default="ONLY_ONE",
        items=[
            ("ADDON_UNREGISTER", "When the plugin logs out",
             "Every time the plugin logout will be automatically backed up once (will be triggered when you close the plugin or close Blender), if you frequently switch on and off Blender will have a lot of backup files"),
            ("ADDON_UNREGISTER_DAY", "When the plugin is logged out (one copy per day is retained)",
             "Keep only one copy per day"),
            ("ONLY_ONE", "Keep only one copy", "Keep only one copy")
        ]
    )

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        from ..ops.export_import import get_backups_folder
        pref = get_pref()
        backups = pref.backups_property
        column = layout.column(heading="Auto Backups")

        box = column.box()
        box.operator("wm.url_open", text="Open Backups Folder").url = get_backups_folder(True)
        box.prop(backups, 'auto_backups')
        box.prop(backups, 'backups_file_mode')
        box.prop(backups, 'enabled_backups_to_specified_path')
        if backups.enabled_backups_to_specified_path:
            box.prop(backups, 'backups_path')


class BackupsPreferences:
    @staticmethod
    def _preferences_backups_path() -> str:
        from ..utils.public import get_backups_folder_default
        path = os.path.join(get_backups_folder_default(), 'preferences')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def preferences_backups(self, export_path=None):
        from ..utils.public import get_debug
        if not export_path:
            export_path = self._preferences_backups_path()
        data = get_property(self, exclude=("gesture", "index_gesture", "name", "init_addon"))
        if get_debug('export_import'):
            print("Gesture Backups Preferences", export_path)
        with open(export_path, "w") as file:
            file.write(json.dumps(data, ensure_ascii=True, indent=2))

    def preferences_restore(self, file_path=None):
        from ..utils.public import get_pref, get_debug
        if not file_path:
            file_path = self._preferences_backups_path()
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                data = json.loads(file.read())
                if get_debug('export_import'):
                    print("Gesture Restore Preferences")
                set_property(get_pref(), data)
