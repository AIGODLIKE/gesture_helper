import bpy
from bpy.props import PointerProperty, BoolProperty, StringProperty, IntProperty


class TempDrawProperty(bpy.types.PropertyGroup):
    """
    Automatically adding attributes

    Set bpy.context.window_manager.gesture_helper_reg_ui_prop.add_ui_extend_bool_property string value
    Will automatically add a boolean value for the input string under the bpy.context.window_manager.gesture_helper_reg_ui_prop property, or if it doesn't exist, will create a new
    """

    key = "gesture_helper_reg_ui_prop"

    @classmethod
    def register_property(cls):
        bpy.utils.register_class(TempDrawProperty)
        setattr(bpy.types.WindowManager, cls.key, PointerProperty(type=TempDrawProperty))

    @classmethod
    def unregister_property(cls):
        bpy.utils.unregister_class(TempDrawProperty)
        delattr(bpy.types.WindowManager, cls.key)

    @classmethod
    def from_name_get_id(cls, name: str):
        return name.lower().replace(' ', '_').replace(':', '').replace(',', '').replace('(', '').replace(')', '')

    @classmethod
    def temp_prop(cls, name) -> bpy.types.PropertyGroup:
        prop = cls.temp_wm_prop()
        identity = cls.from_name_get_id(name)
        p = getattr(prop, identity, None)
        if not p:
            prop.add_ui_extend_bool_property = identity
        return prop

    @classmethod
    def temp_wm_prop(cls):
        return getattr(bpy.context.window_manager, cls.key, None)

    def update_add_ui_extend_bool_property(self, context):
        name = self.add_ui_extend_bool_property
        # 如果没有则当场新建一个属性
        setattr(
            TempDrawProperty,
            name,
            BoolProperty(
                name=f'{name} Bool Property',
                description='Auto-generated Boolean properties name',
                default=self.default_bool_value,
            )
        )

    add_ui_extend_bool_property: StringProperty(
        name='Adding Expanded Properties',
        description='''When you change this property, you will check if there is any property in this property class.
    If it doesn't, it will add it, because you can't add properties in the UI, so you use this method to add them.
    Add the property when updating the property''',
        update=update_add_ui_extend_bool_property,
    )
    default_bool_value: BoolProperty(name='Adding default values for Boolean properties')


def __get_gesture_index__(self):
    from .utils.public import get_pref
    pref = get_pref()
    if len(pref.gesture) > 0:
        return getattr(pref, "index_gesture", -10)
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
