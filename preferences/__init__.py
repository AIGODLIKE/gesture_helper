import bpy
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    PointerProperty,
    EnumProperty)

from ..utils.rna_register import register_classes_safe, unregister_classes_safe

from .add_element import AddElementProperty
from .backups import BackupsProperty, BackupsPreferences
from .debug import DebugProperty
from .draw import PreferencesDraw
from .draw_property import DrawProperty
from .gesture import GestureProperty
from .other import OtherProperty
from .. import __package__ as base_package
from .. import gesture
from ..utils.public import PublicProperty


class GesturePreferences(PublicProperty,
                         bpy.types.AddonPreferences,
                         BackupsPreferences,
                         PreferencesDraw):
    bl_idname = base_package

    # Legacy only: kept one release so old userpref DNA can migrate to WM/JSON.
    # Runtime UI and persistence use WindowManager.gesture_helper (GestureStore).
    gesture: CollectionProperty(type=gesture.Gesture, options={'SKIP_SAVE'})
    index_gesture: IntProperty(
        name='Gesture index',
        description='Legacy index; runtime uses WindowManager.gesture_helper',
        options={'SKIP_SAVE'},
        default=0,
    )

    draw_property: PointerProperty(type=DrawProperty)
    debug_property: PointerProperty(type=DebugProperty)
    other_property: PointerProperty(type=OtherProperty)
    backups_property: PointerProperty(type=BackupsProperty)
    gesture_property: PointerProperty(type=GestureProperty)
    add_element_property: PointerProperty(type=AddElementProperty)
    enabled: BoolProperty(
        name='Enable gesture',
        description="Enable the gesture system",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())
    show_page: EnumProperty(
        name='Preferences page',
        description='Which preferences page to display',
        items=[
            ('GESTURE', 'Gesture', 'Gesture list and element editor'),
            ('PROPERTY', 'Property', 'Draw, backup, and general settings'),
        ],
    )


    def get_gesture_data(self, get_all: bool = False) -> {}:
        from ..ops.export_import import (
            EXPORT_PROPERTY_ITEM,
            EXPORT_PROPERTY_EXCLUDE,
            EXPORT_PUBLIC_ITEM,
        )
        from ..utils.property import get_property

        def filter_data(filter_dict, exclude_keywords=None):
            if exclude_keywords is None:
                exclude_keywords = []
            res = {}
            element_type = filter_dict.get('element_type', None)

            if element_type:
                operator_type = filter_dict.get("operator_type", None)
                if element_type == "OPERATOR" and f"OPERATOR_{operator_type.upper()}" in EXPORT_PROPERTY_ITEM:
                    element_type = f"OPERATOR_{operator_type.upper()}"

                for i in EXPORT_PROPERTY_ITEM.get(element_type, EXPORT_PUBLIC_ITEM):
                    if i in filter_dict:
                        res[i] = filter_dict[i]
            else:
                res.update(filter_dict)

            if 'element' in filter_dict and len(filter_dict['element']) != 0:  # Filter children
                exclude = exclude_keywords.copy()
                if element_type == "CHILD_GESTURE" and filter_dict.get('direction', None) == "9":  # Bottom gesture: skip direction export
                    exclude.append("direction")
                res['element'] = {k: filter_data(v, exclude) for k, v in filter_dict['element'].items()}

            # Strip default export values
            if "enabled" in res and res['enabled']:  # Enabled is default; skip export
                res.pop("enabled")
            if "enabled_icon" in res and not res['enabled_icon']:  # Skip icon when disabled
                if "enabled_icon" in res:
                    res.pop("enabled_icon")
                if "icon" in res:
                    res.pop("icon")
            if "operator_context" in res and res["operator_context"] == "INVOKE_DEFAULT":  # Default context
                res.pop("operator_context")
            if "operator_type" in res and res["operator_type"] == "OPERATOR":  # Default type
                res.pop("operator_type")
            if "operator_properties" in res and res["operator_properties"] == "{}":  # Default empty props
                res.pop("operator_properties")
            if "main_item" in res and not res["main_item"]:  # Default: not a main action
                res.pop("main_item")

            for k in exclude_keywords:
                if k in res:
                    res.pop(k)
            return res

        data = {}
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None:
            return data
        for index, g in enumerate(gestures):
            if g.selected or get_all:
                origin = get_property(g, EXPORT_PROPERTY_EXCLUDE)
                item = filter_data(origin)
                data[str(index)] = item
        return data

    @property
    def is_show_gesture(self):
        return self.show_page == 'GESTURE'

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


def register():
    gesture.register()
    register_classes_safe(classes_list)


def unregister():
    unregister_classes_safe(classes_list)
    gesture.unregister()
