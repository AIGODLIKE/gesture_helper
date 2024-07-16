import bpy.utils
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    PointerProperty,
    EnumProperty)
from bpy.types import AddonPreferences, PropertyGroup

from .backups import BackupsProperty
from .debug import DebugProperty
from .draw import PreferencesDraw
from .draw_property import DrawProperty
from .gesture import GestureProperty
from .other import OtherProperty
from .. import gesture
from ..element.element_property import ElementAddProperty
from ..utils.public import PublicProperty

AddElementProperty = type('Add Element Property', (ElementAddProperty, PropertyGroup), {})


class GesturePreferences(PublicProperty,
                         AddonPreferences,
                         PreferencesDraw):
    from ..utils.public import ADDON_NAME
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name='手势索引', update=lambda self, context: self.active_gesture.to_temp_kmi())

    draw_property: PointerProperty(type=DrawProperty)
    debug_property: PointerProperty(type=DebugProperty)
    other_property: PointerProperty(type=OtherProperty)
    backups_property: PointerProperty(type=BackupsProperty)
    gesture_property: PointerProperty(type=GestureProperty)
    add_element_property: PointerProperty(type=AddElementProperty)

    enabled: BoolProperty(
        name='启用手势',
        description="""启用禁用整个系统,主要是keymap""",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())
    show_page: EnumProperty(name='显示面板', items=[('GESTURE', 'Gesture', ''), ('PROPERTY', 'Property', '')])

    def get_gesture_data(self, get_all: bool = False) -> {}:
        from ..ops.export_import import EXPORT_PROPERTY_ITEM, EXPORT_PROPERTY_EXCLUDE
        from ..utils import PropertyGetUtils

        def filter_data(dd):
            res = {}
            if 'element_type' in dd:
                t = dd['element_type']
                for i in EXPORT_PROPERTY_ITEM[t]:
                    if i in dd:
                        res[i] = dd[i]
            else:
                res.update(dd)
            if 'element' in dd:
                res['element'] = {k: filter_data(v) for k, v in dd['element'].items()}
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
        layout = self.layout
        self.preferences_draw(layout)


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
