import bpy
from bpy.props import CollectionProperty, BoolProperty, StringProperty, IntProperty, PointerProperty

from ..utils.rna_register import register_classes_safe, unregister_classes_safe

from .gesture_keymap import GestureKeymap
from .gesture_property import GestureProperty
from .gesture_relationship import GestureRelationship
from ..element import Element
from ..element import ElementCURE
from ..element.element_modal_operator import ElementModalOperatorEventItem
from ..element.element_modal_operator_cure import ElementModalOperatorEventCRUE
from ..ops.gesture_cure import GestureCURE
from ..utils.public import PublicProperty
from ..utils.gesture_store import WM_STORE_ATTR


class Gesture(
    GestureKeymap,
    GestureProperty,
    GestureRelationship,

    PublicProperty,

    bpy.types.PropertyGroup,
):
    def update_name(self):
        self.key_restart()

    # Draw gesture overlay with GPU
    element: CollectionProperty(type=Element)
    selected: BoolProperty(default=True)
    description: StringProperty(default="This is a gesture...", name="Description")

    @property
    def description_translate(self) -> str:
        from ..src.translate import __name_translate__
        return __name_translate__(self.description)

    @property
    def name_translate(self) -> str:
        from ..src.translate import __name_translate__
        return __name_translate__(self.name)

    def draw_item(self, layout):
        prop = self.draw_property
        if prop.gesture_show_enabled_button:
            layout.prop(self, 'enabled', text='')
        if prop.gesture_show_keymap:
            sp = layout.split(factor=prop.gesture_keymap_split_factor)
            sp.label(text=self.__key_str__)
            layout = sp.row(align=True)
        layout.separator()
        layout.label(text=self.name_translate, translate=False)
        if prop.gesture_show_description:
            layout.label(text=self.description_translate)


def _on_store_index_gesture_update(self, _context):
    try:
        if len(self.gesture):
            self.gesture[self.index_gesture].to_temp_kmi()
    except (IndexError, AttributeError, TypeError, RuntimeError):
        ...


class GestureStore(bpy.types.PropertyGroup):
    """In-memory gesture list for the current Blender session (not userpref)."""

    gesture: CollectionProperty(type=Gesture, options={"SKIP_SAVE"})
    index_gesture: IntProperty(
        name="Gesture index",
        description="Index of the active gesture in the list",
        options={"SKIP_SAVE"},
        update=_on_store_index_gesture_update,
    )


classes_list = (
    ElementModalOperatorEventItem,
    ElementModalOperatorEventCRUE.ADD,
    ElementModalOperatorEventCRUE.COPY,
    ElementModalOperatorEventCRUE.REMOVE,
    ElementModalOperatorEventCRUE.SelectControlProperty,

    Element,
    ElementCURE.ADD,
    ElementCURE.SORT,
    ElementCURE.COPY,
    ElementCURE.CUT,
    ElementCURE.MOVE,
    ElementCURE.REMOVE,
    ElementCURE.SwitchShowChild,

    Gesture,
    GestureCURE.ADD,
    GestureCURE.SORT,
    GestureCURE.COPY,
    GestureCURE.REMOVE,

    GestureStore,
)


def register():
    register_classes_safe(classes_list)
    setattr(
        bpy.types.WindowManager,
        WM_STORE_ATTR,
        PointerProperty(type=GestureStore, options={"SKIP_SAVE"}),
    )


def unregister():
    if hasattr(bpy.types.WindowManager, WM_STORE_ATTR):
        delattr(bpy.types.WindowManager, WM_STORE_ATTR)
    unregister_classes_safe(classes_list)
