from bpy.props import BoolProperty
from bpy.types import PropertyGroup


class OtherProperty(PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name='自动更新操作属性')
    is_move_element: BoolProperty(
        default=False,
        description='移动元素 整个元素需要只有移动操作符可用',
        options={"SKIP_SAVE"})
    init_addon: BoolProperty(name="已初始化插件", default=False)
