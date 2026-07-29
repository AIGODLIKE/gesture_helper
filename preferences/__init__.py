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
from ..utils.enum import LAYOUT_CONTAINER_TYPES


def _update_enabled(_self, _context) -> None:
    gesture.GestureKeymap.key_restart()


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
        default=True,
        update=_update_enabled,
    )
    show_page: EnumProperty(
        name='Preferences page',
        description='Which preferences page to display',
        items=[
            ('GESTURE', 'Gesture', 'Gesture list and element editor'),
            ('PROPERTY', 'Property', 'Gesture, backup, and general settings'),
            ('STYLE', 'Style', 'Overlay appearance and color settings'),
        ],
    )


    def get_gesture_data(self, get_all: bool = False) -> {}:
        from ..ops.export_import import (
            EXPORT_PROPERTY_ITEM,
            EXPORT_PROPERTY_EXCLUDE,
            EXPORT_PUBLIC_ITEM,
        )
        from ..utils.property import get_property

        def filter_data(filter_dict, exclude_keywords=None, source=None):
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

                child_source = getattr(source, 'element', None)

                def get_child_source(key):
                    if child_source is None:
                        return None
                    try:
                        return child_source[int(key)]
                    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                        return None

                res['element'] = {
                    k: filter_data(v, exclude, get_child_source(k))
                    for k, v in filter_dict['element'].items()
                }

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
            if "layout_alignment" in res and res["layout_alignment"] == "EXPAND":
                res.pop("layout_alignment")
            if "layout_align" in res:
                default_align = element_type != 'SPLIT'
                if bool(res["layout_align"]) is default_align:
                    res.pop("layout_align")
            if "layout_round_corners" in res and res["layout_round_corners"]:
                res.pop("layout_round_corners")
            if "layout_align_separators" in res and res["layout_align_separators"]:
                res.pop("layout_align_separators")
            if "split_factor" in res and res["split_factor"] == 0.0:
                res.pop("split_factor")
            if element_type in LAYOUT_CONTAINER_TYPES:
                scale_x = res.get("layout_scale_x")
                scale_y = res.get("layout_scale_y")

                # Old AddonPreferences DNA can still contain only an explicit
                # legacy scale while the newly added axes remain at defaults.
                # Preserve that value until the normal import migration runs.
                is_property_set = getattr(source, 'is_property_set', None)
                if callable(is_property_set):
                    try:
                        if (
                                is_property_set('layout_scale')
                                and not is_property_set('layout_scale_x')
                                and not is_property_set('layout_scale_y')
                        ):
                            scale_x = scale_y = res.get('layout_scale')
                            if scale_x is not None:
                                res['layout_scale_x'] = scale_x
                                res['layout_scale_y'] = scale_y
                    except (AttributeError, ReferenceError, RuntimeError, TypeError):
                        pass

                if scale_x is not None and scale_y is not None:
                    # Keep uniform values readable by older add-on versions.
                    # A non-uniform pair has no faithful legacy representation.
                    if scale_x == scale_y:
                        res["layout_scale"] = scale_x
                    else:
                        res.pop("layout_scale", None)
            if "layout_scale" in res and res["layout_scale"] == 1.0:
                res.pop("layout_scale")
            if "layout_scale_x" in res and res["layout_scale_x"] == 1.0:
                res.pop("layout_scale_x")
            if "layout_scale_y" in res and res["layout_scale_y"] == 1.0:
                res.pop("layout_scale_y")

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
                item = filter_data(origin, source=g)
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
