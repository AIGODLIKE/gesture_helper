from functools import cache

import bpy
from bpy.props import CollectionProperty, IntProperty, BoolProperty

from .element import Element, ElementCURE
from .key import GestureKey
from ..public import PublicOperator, PublicUniqueNamePropertyGroup, get_pref, PublicSortAndRemovePropertyGroup


class GestureProperty(GestureKey):
    def update_index(self, context):
        try:
            el = self.element.values().index(self.index_element)
            if el:
                el.selected = True
        except IndexError:
            ...

    element: CollectionProperty(type=Element)
    index_element: IntProperty(name='索引', update=update_index)

    enabled: BoolProperty(
        name='启用此手势',
        description="""启用禁用此手势,主要是keymap的更新""",
        default=True,
        update=lambda self, context: self.key_update()
    )

    @property
    def element_iteration(self):
        return get_element_iteration(self.element)

    @property
    def collection_iteration(self) -> list:
        return get_pref().gesture.values()

    def _get_index(self) -> int:
        return get_element_index(self)

    def _set_index(self, value: int) -> None:
        self.pref.index_gesture = value

    index = property(fget=_get_index, fset=_set_index, doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def collection(self):
        return self.pref.gesture

    @property
    def is_enable(self) -> bool:
        """
        @rtype: bool
        """
        return self.pref.enabled and self.enabled


class GestureCURE(GestureProperty,
                  PublicSortAndRemovePropertyGroup
                  ):
    # TODO
    # def copy(self, from_element):
    #     ...

    class GesturePoll(PublicOperator):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_gesture is not None

    class ADD(PublicOperator):
        bl_idname = 'gesture.gesture_add'
        bl_label = '添加手势'

        def execute(self, context):
            add = self.pref.gesture.add()
            add.name = 'Gesture'
            return {"FINISHED"}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

        def execute(self, context):
            act = self.pref.active_gesture
            act.key_unload()
            act.remove()
            return {"FINISHED"}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, context):
            self.pref.active_gesture.sort(self.is_next)
            return {"FINISHED"}


@cache
def get_element_iteration(gesture: 'bpy.types.PropertyGroup') -> [Element]:
    items = []
    for e in gesture:
        items.extend(e.element_iteration)
    return items


@cache
def get_element_index(gesture: 'Gesture') -> int:
    return gesture.pref.gesture.values().index(gesture)


class GestureUiDraw(GestureCURE,
                    PublicUniqueNamePropertyGroup):

    def draw_ui(self, layout):
        layout.prop(self, 'enabled', text='')
        layout.separator()
        layout.prop(self, 'name', text='')


class Gesture(GestureUiDraw):
    # 使用gpu绘制在界面上
    def draw(self, operator):
        ...


operator_list = (
    ElementCURE.ADD,
    ElementCURE.REMOVE,
    ElementCURE.MOVE,
    ElementCURE.SORT,

    Element,

    GestureCURE.ADD,
    GestureCURE.REMOVE,
    GestureCURE.SORT,
    Gesture,
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
