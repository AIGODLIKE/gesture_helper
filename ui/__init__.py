import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty
from bpy.types import PropertyGroup


class Extend(PropertyGroup):
    """
    用于存放展开属性,如果没有可以用add_ui_extend_bool_property
    自动添加属性"""

    def update_add_ui_extend_bool_property(self, context):
        name = self.add_ui_extend_bool_property
        # 如果没有则当场新建一个属性
        setattr(Extend, name, bpy.props.BoolProperty(name=f'{name} 展开布尔属性',
                                                     description=f'自动生成的布尔属性',
                                                     default=self.default_bool_value,
                                                     )
                )

    add_ui_extend_bool_property: StringProperty(name='添加展开属性',
                                                description='''更改此属性时会查询此属性类里面有没有此属性
    如果没有,将会添加,因为在UI里面不能添加属性,所以使用此方法来添加
    在更新此属性时添加属性''',
                                                update=update_add_ui_extend_bool_property,
                                                )
    default_bool_value: BoolProperty(name='添加布尔属性的默认值')


mod_tuple = ()


def register():
    for mod in mod_tuple:
        mod.register()
    bpy.utils.register_class(Extend)
    bpy.types.WindowManager.gesture_helper = PointerProperty(type=Extend)


def unregister():
    for mod in mod_tuple:
        mod.unregister()
    bpy.utils.unregister_class(Extend)
    del bpy.types.WindowManager.gesture_helper
