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
    show_page: EnumProperty(name='Show panel', items=[('GESTURE', 'Gesture', ''), ('PROPERTY', 'Property', '')])

    def get_gesture_data(self, get_all: bool = False) -> {}:
        from ..ops.export_import import EXPORT_PROPERTY_ITEM, EXPORT_PROPERTY_EXCLUDE
        from ..utils import PropertyGetUtils

        def filter_data(filter_dict):
            res = {}
            if 'element_type' in filter_dict:
                et = filter_dict['element_type']
                ot = filter_dict.get("operator_type", None)
                if et == "OPERATOR" and f"OPERATOR_{ot}" in EXPORT_PROPERTY_ITEM:
                    et = f"OPERATOR_{ot}"
                for i in EXPORT_PROPERTY_ITEM[et]:
                    if i in filter_dict:
                        res[i] = filter_dict[i]
            else:
                res.update(filter_dict)
            if 'element' in filter_dict and len(filter_dict['element']) != 0:
                res['element'] = {k: filter_data(v) for k, v in filter_dict['element'].items()}
            return res

        data = {}
        for index, g in enumerate(self.pref.gesture):
            if g.selected or get_all:
                origin = PropertyGetUtils.props_data(g, EXPORT_PROPERTY_EXCLUDE)
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
