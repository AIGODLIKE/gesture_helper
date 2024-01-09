import bpy
from bpy.props import PointerProperty, BoolProperty, StringProperty
from bpy_types import PropertyGroup
from bpy.app.translations import pgettext as _

class TempDrawProperty(PropertyGroup):
    """
    用于存放展开属性,如果没有可以用add_ui_extend_bool_property
    自动添加属性"""

    @staticmethod
    def key():
        from .public import ADDON_NAME
        return ADDON_NAME + '_reg_ui_prop'

    @classmethod
    def reg(cls):
        bpy.utils.register_class(TempDrawProperty)
        setattr(bpy.types.WindowManager, cls.key(), PointerProperty(type=TempDrawProperty))

    @classmethod
    def un_reg(cls):
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
                name=_(f'{name} Expand Boolean Property'),
                description=_(f'Auto-generated Boolean Property'),
                default=self.default_bool_value,
            )
        )

    add_ui_extend_bool_property: StringProperty(
        name=_('Add Expand Property'),
        description=_('''When modifying this property, it will check if this property exists in the property class. If not, it will be added, because properties cannot be added in the UI, this method is used to add them. Add the property when updating this property'''),
        update=update_add_ui_extend_bool_property,
    )
    default_bool_value: BoolProperty(name='Add Default Value for Boolean Property')


def register():
    TempDrawProperty.reg()


def unregister():
    TempDrawProperty.un_reg()
