# TODO 导入需要显示一些预设
import json
import os
import time
from datetime import datetime

import bpy
from bpy.props import BoolProperty, StringProperty

from ..ui.ui_list import ImportPresetUIList
from ..utils import PropertyGetUtils
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
        print(self.bl_idname)
        print(self.filepath)
        print('execute')
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        row.label(text='导入预设')
        for k, v in self.preset_items:
            ops = row.operator(self.bl_idname, text=k)
            ops.filepath = v
            ops.preset_show = False


class Export(PublicFileOperator):
    bl_label = '导出手势'
    bl_idname = 'gesture.export'

    author: StringProperty(name='作者')
    description: StringProperty(name='描述')

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
        data = []
        for g in self.pref.gesture:
            if g.selected:
                exclude = ('selected', 'relationship', 'show_child', 'level',
                           'operator_properties_sync_to_properties',
                           'operator_properties_sync_from_temp_properties')
                data.append(PropertyGetUtils.props_data(g, exclude=exclude))
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
        print(self.export_data)
        print(self.bl_idname)
        print(self.file_name)
        if not len(self.export_data['gesture']):
            self.report({'WARNING'}, "未选择导出项")
        else:
            self.write_json_file()
            self.report({'INFO'}, "导出完成!")
        return {'FINISHED'}

    def write_json_file(self):
        with open(self.file_name, 'w+') as file:
            json.dump(self.export_data, file, ensure_ascii=True, indent=2)
