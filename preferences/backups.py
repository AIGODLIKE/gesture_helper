import json
import os

import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty
from bpy.types import PropertyGroup

from ..utils import PropertyGetUtils, PropertySetUtils
from ..utils.public import BACKUPS_FOLDER


class BackupsProperty(PropertyGroup):
    from ..utils.public import ADDON_FOLDER
    auto_backups: BoolProperty(
        name='Enable auto backups',
        description='Automatically save the data every time you log out of the plugin to avoid data loss due to misuse, the path of the autosave is in the “auto_backups” folder of the plugin path.',
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
        default=os.path.join(ADDON_FOLDER, 'auto_backups')
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
    __preferences_backups_path__ = os.path.join(BACKUPS_FOLDER, 'preferences')

    def preferences_backups(self):
        data = PropertyGetUtils.props_data(self, exclude=("gesture", "index_gesture", "name"))
        print("Gesture Backups Preferences", self.__preferences_backups_path__)
        with open(self.__preferences_backups_path__, "w") as file:
            file.write(json.dumps(data, ensure_ascii=True, indent=2))

    def preferences_restore(self):
        if os.path.exists(self.__preferences_backups_path__):
            with open(self.__preferences_backups_path__, "r") as file:
                data = json.loads(file.read())
                print("Gesture Restore Preferences")
                PropertySetUtils.set_property_data(self, data)
