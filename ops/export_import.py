# 导入需要显示一些预设
import json
import os
import time
from datetime import datetime

import bpy
from bpy.props import BoolProperty, StringProperty

from ..gesture import GestureKeymap
from ..ui.ui_list import ImportPresetUIList
from ..utils import PropertySetUtils
from ..utils.public import PublicOperator, PublicProperty, get_pref, get_debug
from ..utils.public_cache import cache_update_lock

EXPORT_PROPERTY_EXCLUDE = ('selected', 'relationship', 'show_child', 'level', 'index_element',
                           'operator_properties_sync_to_properties',
                           'operator_properties_sync_from_temp_properties')

EXPORT_PUBLIC_ITEM = ['name', 'element_type', 'enabled', 'description']
EXPORT_PROPERTY_ITEM = {
    'SELECTED_STRUCTURE': [*EXPORT_PUBLIC_ITEM, 'selected_type', 'poll_string'],
    'CHILD_GESTURE': [*EXPORT_PUBLIC_ITEM, 'direction'],
    'OPERATOR': [*EXPORT_PUBLIC_ITEM, 'direction', 'operator_properties', 'operator_context', 'operator_bl_idname',
                 'operator_type', 'operator_script', 'preview_operator_script'],
}


def ymd():
    now = datetime.now()
    # 提取年、月、日
    year = now.year
    month = now.month
    day = now.day
    return f"{year}-{month:02d}-{day:02d}"


def get_backups_folder(user_custom_path: bool = True) -> str:
    from ..utils.public import ADDON_FOLDER
    prop = get_pref().backups_property

    folder_path = os.path.join(ADDON_FOLDER, 'backups')
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

    selected_all: BoolProperty(name='选择所有', get=__get_all__, set=__set_all__)

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
    bl_label = '导入手势'
    bl_idname = 'gesture.gesture_import'
    preset = {}

    @property
    def preset_items(self):
        from ..utils.public import PROPERTY_FOLDER
        if len(Import.preset):
            return Import.preset

        items = {}
        try:
            for f in os.listdir(PROPERTY_FOLDER):
                path = os.path.join(PROPERTY_FOLDER, f)
                if os.path.isfile(path) and f.lower().endswith('.json'):
                    items[f[:-5]] = path
        except Exception as e:
            print(e.args)
        Import.preset = items
        return items

    def execute(self, _):
        if self.preset_show:
            return {'FINISHED'}
        self.gesture_import()
        self.cache_clear()
        self.update_state()
        self.cache_clear()
        GestureKeymap.key_restart()
        Import.preset = {}
        return {'FINISHED'}

    def draw(self, _):
        layout = self.layout
        row = layout.row()

        row.label(text='导入预设')
        column = layout.column(align=True)

        for k, v in self.preset_items.items():
            ops = column.operator(self.bl_idname, text=k)
            ops.filepath = v
            ops.run_execute = True
            ops.preset_show = False

    @cache_update_lock
    def gesture_import(self):
        try:
            data = self.read_json()
            restore = data['gesture']
            # if get_debug('key'):
            #     print('restore', restore)
            PropertySetUtils.set_prop(self.pref, 'gesture', restore)
            auth = data['author']
            des = data['description']
            ver = '.'.join((str(i) for i in data['addon_version']))
            self.report({'INFO'}, f"导入成功! 导入{len(restore)}条数据 作者:{auth} 注释:{des} 版本:{ver}")
        except Exception as e:
            self.report({'ERROR'}, f"导入错误: {e.args}")
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    def read_json(self):
        with open(self.filepath, 'r') as file:
            return json.load(file)

    @staticmethod
    def restore():
        """
        恢复
        """
        try:
            backups_path = get_backups_folder()

            if os.path.isdir(backups_path):
                key = f"Gesture Close Addon Backups {ymd()}.json"
                if key in os.listdir(backups_path):
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
    bl_label = '导出手势'
    bl_idname = 'gesture.export'

    author: StringProperty(name='作者', default='小萌新')
    description: StringProperty(name='描述', default='这是一个描述')
    is_auto_backups: BoolProperty(name="是自动备份", default=False, options={"SKIP_SAVE"})
    is_close_backups: BoolProperty(name="是关闭插件备份", default=False, options={"SKIP_SAVE"})

    @property
    def file_string(self):
        string = datetime.fromtimestamp(time.time())
        mode = self.pref.backups_property
        if self.is_auto_backups:
            if mode == "ADDON_UNREGISTER":
                string = f'Auto Backups {self.date}'
            elif mode == "ADDON_UNREGISTER_DAY":
                string = f'Auto Backups {ymd()}'
            elif mode == "ONLY_ONE":
                string = f'Auto Backups'
        if self.is_close_backups:
            string = f'Close Addon Backups {ymd()}'
        return string

    @property
    def file_path(self):
        folder_path = self.filepath

        if self.is_auto_backups or self.is_close_backups:
            folder_path = get_backups_folder(not self.is_close_backups)
        name = 'Gesture'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if os.path.isfile(folder_path):
            name = os.path.basename(folder_path)
            folder_path = os.path.dirname(folder_path)
        new_name = name if name.endswith('.json') else f'{name} {self.file_string}.json'.replace(':', ' ')
        return os.path.abspath(os.path.join(folder_path, new_name))

    @property
    def export_data(self):
        from .. import ADDON_VERSION
        data = {
            'time': time.time(),
            'blender_version': bpy.app.version,
            'addon_version': ADDON_VERSION,

            'author': self.author,
            'description': self.description,

            'gesture': self.pref.get_gesture_data(self.is_auto_backups or self.is_close_backups)
        }
        return data

    def draw(self, _):
        layout = self.layout

        layout.prop(self, 'author', emboss=True)
        layout.prop(self, 'description', emboss=True)
        layout.separator()

        row = layout.row()
        row.label(text='导出')
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

    def execute(self, _):
        if len(self.pref.gesture) == 0:
            ...
        elif not len(self.export_data['gesture']):
            self.report({'WARNING'}, "未选择导出项")
        else:
            self.write_json_file()
            self.report({'INFO'}, f"导出完成!\t{self.file_path}")
        return {'FINISHED'}

    def write_json_file(self):
        with open(self.file_path, 'w') as file:
            print(f"write_json_file\t{self.file_path}")
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
            print(f"gesture backups\t{is_blender_close}\t{is_auto_backups}")
            bpy.ops.gesture.export(
                'EXEC_DEFAULT',
                author='Emm',
                description='auto_backups',
                is_auto_backups=is_auto_backups,
                is_close_backups=not is_blender_close,
            )
        except Exception as e:
            print("try auto backups error", e.args)
