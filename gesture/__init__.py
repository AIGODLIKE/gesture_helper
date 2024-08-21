import bpy
from bpy.props import CollectionProperty, BoolProperty, StringProperty
from bpy.types import PropertyGroup

from .gesture_keymap import GestureKeymap
from .gesture_property import GestureProperty
from .gesture_relationship import GestureRelationship
from ..element import Element
from ..element import ElementCURE
from ..ops.gesture_cure import GestureCURE
from ..utils.public import PublicProperty


class Gesture(
    GestureKeymap,
    GestureProperty,
    GestureRelationship,

    PublicProperty,

    PropertyGroup,
):
    # 使用gpu绘制在界面上
    element: CollectionProperty(type=Element)
    selected: BoolProperty(default=True)
    description: StringProperty(default="This is a gesture...", name="Description")

    def draw_item(self, layout):
        prop = self.draw_property
        if prop.gesture_show_enabled_button:
            layout.prop(self, 'enabled', text='')
        if prop.gesture_show_keymap:
            sp = layout.split(factor=prop.gesture_keymap_split_factor)
            sp.label(text=self.__key_str__)
            layout = sp.row(align=True)
        layout.separator()
        layout.prop(self, 'name', text='')
        if prop.gesture_show_description:
            layout.label(text=self.description)


classes_list = (
    Element,

    ElementCURE.ADD,
    ElementCURE.SORT,
    ElementCURE.COPY,
    ElementCURE.CUT,
    ElementCURE.MOVE,
    ElementCURE.REMOVE,
    ElementCURE.ScriptEdit,
    ElementCURE.ScriptSave,

    Gesture,

    GestureCURE.ADD,
    GestureCURE.SORT,
    GestureCURE.COPY,
    GestureCURE.REMOVE,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(classes_list)


def register():
    register_classes()
    ElementCURE.ScriptSave.register_ui()


def unregister():
    unregister_classes()
    ElementCURE.ScriptSave.unregister_ui()
    print()
