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
        if TempDrawProperty.is_registered:
            try:
                bpy.utils.unregister_class(TempDrawProperty)
            except RuntimeError:
                pass
        if hasattr(bpy.types.WindowManager, cls.key):
            delattr(bpy.types.WindowManager, cls.key)

    @classmethod
    def temp_wm_prop(cls):
        return getattr(bpy.context.window_manager, cls.key, None)

    def update_add_ui_extend_bool_property(self, context):
        name = self.add_ui_extend_bool_property
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
    from .utils.gesture_store import get_gesture_store
    store = get_gesture_store()
    if store is not None and len(store.gesture) > 0:
        return store.index_gesture
    return -1


def __set_gesture_index__(self, value):
    from .utils.gesture_store import get_gesture_store
    store = get_gesture_store()
    if store is not None:
        store.index_gesture = value


def register():
    TempDrawProperty.register_property()
    bpy.types.WindowManager.gesture_index = IntProperty(get=__get_gesture_index__, set=__set_gesture_index__)


def unregister():
    TempDrawProperty.unregister_property()
    del bpy.types.WindowManager.gesture_index
