import bpy
from bpy.props import PointerProperty, BoolProperty, StringProperty, IntProperty
from bpy_types import PropertyGroup


class TempDrawProperty(PropertyGroup):
    """
    用于存放展开属性,如果没有可以用add_ui_extend_bool_property
    自动添加属性"""

    @staticmethod
    def key():
        from .utils.public import ADDON_NAME
        return ADDON_NAME + '_reg_ui_prop'

    @classmethod
    def register_property(cls):
        bpy.utils.register_class(TempDrawProperty)
        setattr(bpy.types.WindowManager, cls.key(), PointerProperty(type=TempDrawProperty))

    @classmethod
    def unregister_property(cls):
        bpy.utils.unregister_class(TempDrawProperty)
        delattr(bpy.types.WindowManager, cls.key())

    @classmethod
    def from_name_get_id(cls, name: str):
        return name.lower().replace(' ', '_').replace(':', '').replace(',', '').replace('(', '').replace(')', '')

    @classmethod
    def temp_prop(cls, name) -> PropertyGroup:
        prop = cls.temp_wm_prop()
        identity = cls.from_name_get_id(name)
        p = getattr(prop, identity, None)
        if not p:
            prop.add_ui_extend_bool_property = identity
        return prop

    @classmethod
    def temp_wm_prop(cls):
        return getattr(bpy.context.window_manager, cls.key(), None)

    def update_add_ui_extend_bool_property(self, context):
        name = self.add_ui_extend_bool_property
        # 如果没有则当场新建一个属性
        setattr(
            TempDrawProperty,
            name,
            BoolProperty(
                name=f'{name} 展开布尔属性',
                description=f'自动生成的布尔属性',
                default=self.default_bool_value,
            )
        )

    add_ui_extend_bool_property: StringProperty(
        name='添加展开属性',
        description='''更改此属性时会查询此属性类里面有没有此属性
    如果没有,将会添加,因为在UI里面不能添加属性,所以使用此方法来添加
    在更新此属性时添加属性''',
        update=update_add_ui_extend_bool_property,
    )
    default_bool_value: BoolProperty(name='添加布尔属性的默认值')


def __get_gesture_index__(self):
    from .utils.public import get_pref
    pref = get_pref()
    if len(pref.gesture) > 0:
        return pref.index_gesture
    return -1


def __set_gesture_index__(self, value):
    from .utils.public import get_pref
    pref = get_pref()
    pref.index_gesture = value


def register():
    TempDrawProperty.register_property()
    bpy.types.Text.gesture_element_hash = StringProperty()
    bpy.types.WindowManager.gesture_index = IntProperty(get=__get_gesture_index__, set=__set_gesture_index__)


def unregister():
    TempDrawProperty.unregister_property()
    del bpy.types.Text.gesture_element_hash
    del bpy.types.WindowManager.gesture_index
