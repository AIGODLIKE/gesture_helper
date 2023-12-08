# 导入需要显示一些预设
import json
import os
import time
from datetime import datetime

import bpy
from bpy.props import BoolProperty, StringProperty

from ..ui.ui_list import ImportPresetUIList
from ..utils import PropertyGetUtils, PropertySetUtils
from ..utils.gesture import GestureKeymap
from ..utils.public import PublicOperator, PublicProperty, get_pref
from ..utils.public_cache import cache_update_lock

EXPORT_PROPERTY_EXCLUDE = ('selected', 'relationship', 'show_child', 'level', 'index_element',
                           'operator_properties_sync_to_properties',
                           'operator_properties_sync_from_temp_properties')

EXPORT_PUBLIC_ITEM = ['name', 'element_type', 'enabled', 'description']
EXPORT_PROPERTY_ITEM = {
    'SELECTED_STRUCTURE': [*EXPORT_PUBLIC_ITEM, 'selected_type', 'poll_string'],
    'CHILD_GESTURE': [*EXPORT_PUBLIC_ITEM, 'direction'],
    'OPERATOR': [*EXPORT_PUBLIC_ITEM, 'direction', 'operator_properties', 'operator_context', 'operator_bl_idname'],
}


class PublicFileOperator(PublicOperator, PublicProperty):
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={'HIDDEN', 'SKIP_SAVE'}, )
    preset_show: BoolProperty(options={'HIDDEN'}, )
    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    run_execute: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}, )

    def get_all(self):
        pref = get_pref()
        return all((i.selected for i in pref.gesture))

    def set_all(self, value):
        pref = get_pref()
        for i in pref.gesture:
            i.selected = value

    selected_all: BoolProperty(name='选择所有', get=get_all, set=set_all)

    def invoke(self, context, event):
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
    bl_idname = 'gesture.import'
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

    def execute(self, context):
        if self.preset_show:
            return {'FINISHED'}
        self.restore()
        self.cache_clear()
        self.update_state()
        self.cache_clear()
        GestureKeymap.key_restart()
        Import.preset = {}
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        row.label(text='导入预设')
        column = layout.column(align=True)

        for k, v in self.preset_items.items():
            ops = column.operator(self.bl_idname, text=k)
            ops.filepath = v
            ops.run_execute = True

    @cache_update_lock
    def restore(self):
        try:
            data = self.read_json()
            restore = data['gesture']
            print('restore', restore)
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


class Export(PublicFileOperator):
    bl_label = '导出手势'
    bl_idname = 'gesture.export'

    author: StringProperty(name='作者', default='小萌新')
    description: StringProperty(name='描述', default='这是一个描述')

    @property
    def ymdhm(self):
        return datetime.fromtimestamp(time.time())

    @property
    def file_name(self):
        folder = self.filepath
        name = 'Gesture'
        if not os.path.exists(folder) or os.path.isfile(folder):
            name = os.path.basename(folder)
            folder = os.path.dirname(folder)
        new_name = name if name.endswith('.json') else f'{name} {self.ymdhm}.json'.replace(':', ' ')

        return os.path.abspath(os.path.join(folder, new_name))

    @property
    def gesture_data(self):

        def filter_data(dd):
            res = {}
            if 'element_type' in dd:
                t = dd['element_type']
                for i in EXPORT_PROPERTY_ITEM[t]:
                    if i in dd:
                        res[i] = dd[i]
            else:
                res.update(dd)
            if 'element' in dd:
                res['element'] = {k: filter_data(v) for k, v in dd['element'].items()}
            return res

        data = {}
        for index, g in enumerate(self.pref.gesture):
            if g.selected:
                origin = PropertyGetUtils.props_data(g, EXPORT_PROPERTY_EXCLUDE)
                item = filter_data(origin)
                data[str(index)] = item
        return data

    @property
    def export_data(self):
        from .. import ADDON_VERSION
        data = {
            'time': time.time(),
            'blender_version': bpy.app.version,
            'addon_version': ADDON_VERSION,

            'author': self.author,
            'description': self.description,

            'gesture': self.gesture_data
        }
        return data

    def draw(self, context):
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

    def execute(self, context):
        if not len(self.export_data['gesture']):
            self.report({'WARNING'}, "未选择导出项")
        else:
            self.write_json_file()
            self.report({'INFO'}, "导出完成!")
        return {'FINISHED'}

    def write_json_file(self):
        with open(self.file_name, 'w+') as file:
            json.dump(self.export_data, file, ensure_ascii=True, indent=2)

    @staticmethod
    def backups():
        from ..utils.public import ADDON_FOLDER
        file_path = os.path.join(ADDON_FOLDER, 'auto_backups')
        try:
            if get_pref().other_property.auto_backups:
                bpy.ops.gesture.export('EXEC_DEFAULT', author='Emm', description='auto_backups', filepath=file_path)
        except Exception as e:
            print(e.args)
