# TODO 导入需要显示一些预设
import bpy
from bpy.props import BoolProperty, EnumProperty

from ..utils.public import PublicOperator


class PublicFileOperator(PublicOperator):
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    preset_type: EnumProperty(name='预设类型 TODO',
                              items=[('ELEMENT', 'Element', ''), ('GESTURE', 'Gesture', '')])

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class Import(PublicFileOperator):
    bl_label = '导入手势'
    bl_idname = 'gesture.import'

    preset_draw_show: BoolProperty()

    def invoke(self, context, event):
        if self.show_preset:
            return context.window_manager.invoke_props_popup(**{'operator': self, 'width': 300})
        else:
            return super().invoke(context, event)

    def execute(self, context):
        print(self.bl_idname)
        print(self.filepath)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout.column()
        layout.emboss = 'NONE'
        layout.label(text='预设')


class Export(PublicFileOperator):
    bl_label = '导出手势'
    bl_idname = 'gesture.export'

    def execute(self, context):
        print(self.bl_idname)
        print(self.filepath)
        return {'FINISHED'}
