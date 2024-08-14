from bpy.props import BoolProperty
from bpy.types import PropertyGroup


class OtherProperty(PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name='自动更新操作属性')
    init_addon: BoolProperty(name="已初始化插件", default=False)
