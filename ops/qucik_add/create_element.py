import bpy
from bpy.props import EnumProperty

from ...utils.public import PublicOperator, PublicProperty


class CreateElement(PublicOperator, PublicProperty):
    bl_label = '创建元素'
    bl_idname = 'gesture.create_element'

    mode: EnumProperty(items=[('OPERATOR', '操作符', ''), ('PROPERTY', '属性', '')], name='模式',
                       options={'HIDDEN', 'SKIP_SAVE'})
    boolean_mode: EnumProperty(
        items=[('SET_TRUE', '设置为 True', ''), ('SET_FALSE', '设置为 False', ''), ('SWITCH', '切换', '')],
        name='布尔模式',
        options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        bpy.ops.ui.copy_data_path_button(full_path=True)

        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        button_operator = getattr(context, "button_operator", None)
        print(self.bl_idname, button_pointer, button_prop, button_operator)
        print(bpy.context.window_manager.clipboard)
        return {'FINISHED'}
