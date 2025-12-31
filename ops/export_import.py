# 导入需要显示一些预设
import json
import os
import time
from datetime import datetime

import bpy
from bpy.app.translations import pgettext
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..gesture import GestureKeymap
from ..ui.ui_list import ImportPresetUIList
from ..utils.property import __set_prop__
from ..utils.public import PublicOperator, PublicProperty, get_pref
from ..utils.public_cache import cache_update_lock

EXPORT_PROPERTY_EXCLUDE = (
    'selected',
    'relationship',
    'show_child',
    'level',
    'index_element',
    'operator_properties_sync_to_properties',
    'operator_properties_sync_from_temp_properties',
    'preview_operator_script',
)

EXPORT_ICON_ITEM = ['icon', 'enabled_icon']
EXPORT_PUBLIC_ITEM = ['name', 'element_type', 'enabled', 'description']
EXPORT_PROPERTY_ITEM = {
    'SELECTED_STRUCTURE': [*EXPORT_PUBLIC_ITEM, 'selected_type', 'poll_string'],
    'CHILD_GESTURE': [*EXPORT_PUBLIC_ITEM, *EXPORT_ICON_ITEM, 'direction'],
    'OPERATOR_SCRIPT': [
        *EXPORT_PUBLIC_ITEM,
        *EXPORT_ICON_ITEM,
        'direction', 'operator_type', 'operator_script', ],
    'OPERATOR_MODAL': [
        *EXPORT_PUBLIC_ITEM,
        *EXPORT_ICON_ITEM,
        'modal_events',
        'modal_events_index',
        'control_property',
        'number_value_mode',
        'float_incremental_value',
        'float_value',
        'int_incremental_value',
        'int_value',
        'bool_value_mode',
        'enum_value_mode',
        'enum_value_a',
        'enum_value_b',
        'enum_reverse',
        'enum_wrap',
        'event_type',
        'event_ctrl',
        'event_alt',
        'operator_bl_idname',
        'event_shift',
        'direction', 'operator_type'],
    'OPERATOR_OPERATOR': [
        *EXPORT_PUBLIC_ITEM,
        *EXPORT_ICON_ITEM,
        'direction', 'operator_bl_idname', 'operator_context', 'operator_properties', ],
    "DIVIDING_LINE": [*EXPORT_PUBLIC_ITEM]
}


def ymd() -> str:
    """提取 '年-月-日'"""
    now = datetime.now()

    year = now.year
    month = now.month
    day = now.day
    return f"{year}-{month:02d}-{day:02d}"


def get_backups_folder(user_custom_path: bool = True) -> str:
    from ..utils.public import BACKUPS_FOLDER
    prop = get_pref().backups_property

    folder_path = BACKUPS_FOLDER
    if prop.enabled_backups_to_specified_path and user_custom_path:
        if os.path.isdir(prop.backups_path):
            folder_path = prop.backups_path
    return folder_path


class PublicFileOperator(PublicOperator, PublicProperty):
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={'HIDDEN', 'SKIP_SAVE'}, )
    preset_show: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'}, )
    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    run_execute: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}, )

    def __get_all__(self):
        pref = get_pref()
        return all((i.selected for i in pref.gesture))

    def __set_all__(self, value):
        pref = get_pref()
        for i in pref.gesture:
            i.selected = value

    selected_all: BoolProperty(name='Select all', get=__get_all__, set=__set_all__)

    def invoke(self, context, _):
        if self.run_execute:
            return self.execute(context)
        elif self.preset_show:
            wm = context.window_manager
            return wm.invoke_props_dialog(**{'operator': self, 'width': 300})
        else:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}


class Import(PublicFileOperator):
    bl_label = 'Import gesture'
    bl_idname = 'gesture.gesture_import'
    preset = {}

    @property
    def preset_items(self):
        from ..utils.preset import get_preset_gesture_list
        if len(Import.preset):
            return Import.preset
        Import.preset = get_preset_gesture_list()
        return Import.preset

    def execute(self, _):
        if self.preset_show:
            return {'FINISHED'}
        self.gesture_import()
        self.cache_clear()
        self.update_state()
        self.cache_clear()
        Import.preset = {}
        GestureKeymap.key_restart()
        bpy.ops.wm.save_userpref()
        self.cache_clear()
        return {'FINISHED'}

    def draw(self, _):
        layout = self.layout
        row = layout.row()

        row.label(text='Import preset')
        column = layout.column(align=True)

        for k, v in self.preset_items.items():
            ops = column.operator(self.bl_idname, text=self.__tp__(k))
            ops.filepath = v
            ops.run_execute = True
            ops.preset_show = False

    @cache_update_lock
    def gesture_import(self):
        try:
            from ..gesture import gesture_keymap

            data = self.read_json()
            restore = data['gesture']
            __set_prop__(self.pref, 'gesture', restore)
            gesture_keymap.GestureKeymap.key_restart()

            auth = data['author']
            des = data['description']
            ver = '.'.join((str(i) for i in data['addon_version']))

            text = pgettext(
                r"Imported successfully! Imported %s of data Author:%s Comments:%s Exported data addon version:%s") % (
                       len(restore), auth, des, ver)
            self.report({'INFO'}, text)
        except Exception as e:
            self.report({'ERROR'}, f"{pgettext('Import error')}: {e.args}")
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    def read_json(self):
        with open(self.filepath, 'r') as file:
            return json.load(file)

    @staticmethod
    def restore():
        """
        恢复数据
        """
        try:
            backups_path = get_backups_folder()
            print("try restore", backups_path)
            if os.path.isdir(backups_path):
                key = f"Gesture Close Addon Backups {ymd()}.json"
                if key in os.listdir(backups_path):
                    print("check restore file", backups_path)
                    bpy.ops.gesture.gesture_import(
                        # 'EXEC_DEFAULT',
                        filepath=os.path.join(backups_path, key),
                        run_execute=True,
                    )
            else:
                print("try load gesture config, not found backups folder")
        except Exception as e:
            print("try auto restore error", e.args)


class Export(PublicFileOperator):
    bl_label = 'Export gesture'
    bl_idname = 'gesture.export'

    description: StringProperty(name='Description', default='This is a description')
    is_auto_backups: BoolProperty(name="Is auto backups", default=False, options={"SKIP_SAVE"})
    is_close_backups: BoolProperty(name="Is close backups", default=False, options={"SKIP_SAVE"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_invoke = False

    @property
    def file_string(self):
        string = datetime.fromtimestamp(time.time())
        mode = self.pref.backups_property.backups_file_mode
        if self.is_auto_backups:
            if mode == "ADDON_UNREGISTER":
                string = f"Auto Backups {string}"
            elif mode == "ADDON_UNREGISTER_DAY":
                string = f"Auto Backups {ymd()}"
            elif mode == "ONLY_ONE":
                string = "Auto Backups"
        if self.is_close_backups:
            string = f"Close Addon Backups {ymd()}"
        return string

    @property
    def file_path(self):
        folder_path = self.filepath
        name = "Gesture"

        if self.is_invoke and folder_path.endswith('.json'):
            return os.path.abspath(folder_path)

        elif self.is_auto_backups or self.is_close_backups:
            folder_path = get_backups_folder(not self.is_close_backups)
            return os.path.abspath(os.path.join(folder_path, f'{name} {self.file_string}.json'.replace(':', ' ')))

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if os.path.isfile(folder_path) and not self.is_auto_backups:
            # 选择了一个文件覆盖
            name = os.path.basename(folder_path)
            folder_path = os.path.dirname(folder_path)
            return os.path.abspath(os.path.join(folder_path, name))
        else:
            return os.path.abspath(os.path.join(folder_path, f'Gesture {datetime.now()}.json'.replace(':', ' ')))

    @property
    def export_data(self):
        from .. import ADDON_VERSION
        data = {
            'time': time.time(),
            'blender_version': bpy.app.version,
            'addon_version': ADDON_VERSION,

            'author': self.pref.draw_property.author,
            'description': self.description,

            'gesture': self.pref.get_gesture_data(self.is_auto_backups or self.is_close_backups)
        }
        return data

    def draw(self, _):
        layout = self.layout

        layout.prop(self.pref.draw_property, 'author', emboss=True)
        layout.prop(self, 'description', emboss=True)
        layout.separator()

        row = layout.row()
        row.label(text='Export')
        row.prop(self, 'selected_all', emboss=True)

        column = layout.column()
        column.template_list(
            ImportPresetUIList.bl_idname,
            ImportPresetUIList.bl_idname,
            self.pref,
            'gesture',
            self.pref,
            'index_gesture',
        )

    def invoke(self, context, event):
        self.is_invoke = True
        return super().invoke(context, event)

    def execute(self, _):
        if len(self.pref.gesture) == 0:
            return {'CANCELLED'}
        elif not len(self.export_data['gesture']):
            self.report({'WARNING'}, "Export Item Not Selected")
        else:
            self.write_json_file()
            self.report({'INFO'}, pgettext("Export Finished! %s") % self.file_path)
        return {'FINISHED'}

    def write_json_file(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.export_data, file, ensure_ascii=True, indent=2)

    @staticmethod
    def backups(is_blender_close: bool = False):
        """
        只在关闭插件时进行操作
        备份分为两种,
        一种是关闭插件,一种是关闭Blender
        """
        try:
            is_auto_backups = get_pref().backups_property.auto_backups
            print(f"Gesture Auto Backups\tis_blender_close:{is_blender_close}\tis_auto_backups:{is_auto_backups}")
            bpy.ops.gesture.export(
                'EXEC_DEFAULT',
                filepath='',
                description='auto_backups',
                is_auto_backups=is_auto_backups,
                is_close_backups=not is_blender_close,
            )
        except Exception as e:
            print("try auto backups error", e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()


class ExportPreferences(bpy.types.Operator, ExportHelper):
    bl_idname = "gesture.export_preferences"
    bl_label = "Export Preferences"

    filename_ext = ".gesture_preferences"

    def execute(self, context):
        from ..utils.public import get_pref
        from bpy.app.translations import pgettext_iface
        try:
            get_pref().preferences_backups(self.filepath)
        except Exception as e:
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            print(e.args)
            self.report({'ERROR'}, pgettext_iface("Export error, please check path %s") % self.filepath)
        return {"FINISHED"}


class ImportPreferences(bpy.types.Operator, ImportHelper):
    bl_idname = "gesture.import_preferences"
    bl_label = "Import Preferences"

    def execute(self, context):
        from ..utils.public import get_pref
        try:
            get_pref().preferences_restore(self.filepath)
        except Exception as e:
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            print(e.args)
            self.report({'ERROR'}, "Import error, please select preference settings file")
        return {"FINISHED"}
