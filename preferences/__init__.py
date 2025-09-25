import bpy
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    PointerProperty,
    EnumProperty)

from .backups import BackupsProperty, BackupsPreferences
from .debug import DebugProperty
from .draw import PreferencesDraw
from .draw_property import DrawProperty
from .gesture import GestureProperty
from .other import OtherProperty
from .. import __package__ as base_package
from .. import gesture
from ..element.element_property import ElementAddProperty
from ..utils.public import PublicProperty

AddElementProperty = type('Add Element Property', (ElementAddProperty, bpy.types.PropertyGroup), {})


class GesturePreferences(PublicProperty,
                         bpy.types.AddonPreferences,
                         BackupsPreferences,
                         PreferencesDraw):
    bl_idname = base_package

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name='Gesture index', update=lambda self, context: self.active_gesture.to_temp_kmi())

    draw_property: PointerProperty(type=DrawProperty)
    debug_property: PointerProperty(type=DebugProperty)
    other_property: PointerProperty(type=OtherProperty)
    backups_property: PointerProperty(type=BackupsProperty)
    gesture_property: PointerProperty(type=GestureProperty)
    add_element_property: PointerProperty(type=AddElementProperty)

    enabled: BoolProperty(
        name='Enable gesture',
        description="""Enable gesture system""",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())
    show_page: EnumProperty(name='Show panel',
                            items=[('GESTURE', 'Gesture', ''),
                                   ('PROPERTY', 'Property', ''),
                                   ('DEBUG', 'Debug', '')])

    def get_gesture_data(self, get_all: bool = False) -> {}:
        from ..ops.export_import import EXPORT_PROPERTY_ITEM, EXPORT_PROPERTY_EXCLUDE
        from ..utils.property import get_property

        def filter_data(filter_dict, exclude_keywords=[]):
            res = {}
            if 'element_type' in filter_dict:
                element_type = filter_dict['element_type']
                operator_type = filter_dict.get("operator_type", None)
                if element_type == "OPERATOR" and f"OPERATOR_{operator_type}" in EXPORT_PROPERTY_ITEM:
                    element_type = f"OPERATOR_{operator_type}"
                for i in EXPORT_PROPERTY_ITEM[element_type]:
                    if i in filter_dict:
                        res[i] = filter_dict[i]
            else:
                res.update(filter_dict)
            if 'element' in filter_dict and len(filter_dict['element']) != 0:
                res['element'] = {k: filter_data(v) for k, v in filter_dict['element'].items()}

            if res.get('enabled', False):  # 默认为开启,不需要导出
                res.pop("enabled")
            if "enabled_icon" in res:  # 如果没启用图标就不导出图标数据
                if not res["enabled_icon"]:
                    if "enabled_icon" in res:
                        res.pop("enabled_icon")
                    if "icon" in res:
                        res.pop("icon")
            if "operator_context" in res and res["operator_context"] == "INVOKE_DEFAULT":
                # 默认值为INVOKE_DEFAULT
                res.pop("operator_context")
            for k in exclude_keywords:
                if k in res:
                    res.pop(k)
            return res

        data = {}
        for index, g in enumerate(self.pref.gesture):
            if g.selected or get_all:
                origin = get_property(g, EXPORT_PROPERTY_EXCLUDE)
                item = filter_data(origin)
                data[str(index)] = item
        return data

    @property
    def is_show_gesture(self):
        return self.show_page == 'GESTURE'

    @property
    def is_show_property(self):
        return self.show_page == 'PROPERTY'

    def draw(self, _):
        self.preferences_draw(self.layout)


classes_list = (
    DrawProperty,
    DebugProperty,
    BackupsProperty,
    OtherProperty,
    GestureProperty,
    AddElementProperty,

    GesturePreferences,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(classes_list)


def register():
    gesture.register()
    register_classes()


def unregister():
    unregister_classes()
    gesture.unregister()
