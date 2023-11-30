# TODO 导入需要显示一些预设
import json
import os
import time
from datetime import datetime

import bpy
from bpy.props import BoolProperty, StringProperty

from ..utils.public_cache import cache_update_lock
from ..ui.ui_list import ImportPresetUIList
from ..utils import PropertyGetUtils, PropertySetUtils
from ..utils.public import PublicOperator, PublicProperty, get_pref


class PublicFileOperator(PublicOperator, PublicProperty):
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={'HIDDEN'}, )
    preset_show: BoolProperty(options={'HIDDEN'}, )
    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def get_all(self):
        pref = get_pref()
        return all((i.selected for i in pref.gesture))

    def set_all(self, value):
        pref = get_pref()
        for i in pref.gesture:
            i.selected = value

    selected_all: BoolProperty(name='选择所有', get=get_all, set=set_all)

    def invoke(self, context, event):
        if self.preset_show:
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
                if os.path.isfile(f) and f.lower().endswith('.json'):
                    items[f] = os.path.join(PROPERTY_FOLDER, f)
        except Exception as e:
            print(e.args)
        Import.preset = items
        return items

    def execute(self, context):
        self.restore()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        row.label(text='导入预设')
        for k, v in self.preset_items:
            ops = row.operator(self.bl_idname, text=k)
            ops.filepath = v
            ops.preset_show = False

    @cache_update_lock
    def restore(self):
        try:
            data = self.read_json()
            restore = {'gesture': data['gesture']}
            PropertySetUtils.set_prop(self.pref, 'gesture', data['gesture'])
        except Exception as e:
            self.report({'ERROR'}, f"导入错误: {e.args}")

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
    def json_name(self):
        return f'Gesture {self.ymdhm}.json'.replace(':', ' ')

    @property
    def file_name(self):
        path = os.path.dirname(self.filepath) if os.path.isfile(self.filepath) else self.filepath
        return os.path.abspath(os.path.join(path, self.json_name))

    @property
    def gesture_data(self):

        item_key = {
            'SELECTED_STRUCTURE': ['name', 'element_type', 'selected_type', 'poll_string'],
            'CHILD_GESTURE': ['name', 'element_type', 'direction'],
            'OPERATOR': ['name', 'element_type', 'operator_properties', 'operator_context', 'operator_bl_idname'],
        }

        def filter_data(d):
            res = {}
            if 'element_type' in d:
                t = d['element_type']
                for k in item_key[t]:
                    res[k] = d[k]
            else:
                res.update(d)
            if 'element' in d:
                res['element'] = {k: filter_data(v) for k, v in d['element'].items()}
            return res

        data = []
        for g in self.pref.gesture:
            if g.selected:
                exclude = ('selected', 'relationship', 'show_child', 'level',
                           'enabled',
                           'operator_properties_sync_to_properties',
                           'operator_properties_sync_from_temp_properties')
                data.append(filter_data(PropertyGetUtils.props_data(g, exclude=exclude)))
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
