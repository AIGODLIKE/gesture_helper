from functools import cache

import bpy
from bpy.props import CollectionProperty, IntProperty, BoolProperty

from .element import Element, ElementCURE
from .key import GestureKey
from ..public import PublicOperator, PublicUniqueNamePropertyGroup, get_pref


class GestureProperty(GestureKey):
    element: CollectionProperty(type=Element)
    index_element: IntProperty(name='索引')

    enable: BoolProperty(
        name='启用此手势',
        description="""启用禁用此手势,主要是keymap的更新""",
        default=True,
        update=lambda self, context: self.key_update()
    )

    @property
    def element_iteration(self) -> [Element]:
        return get_element_iteration(self.element)

    @property
    def _items_iteration(self) -> list:
        return get_pref().gesture.values()

    def _get_index(self) -> int:
        return get_element_index(self)

    def _set_index(self, value: int) -> None:
        self.pref.index_gesture = value

    index = property(fget=_get_index, fset=_set_index, doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def is_last(self) -> bool:
        """
        反回此手势 是否为最后一个的布尔值
        用于移动手势位置
        @rtype: object
        """
        return self == self._items_iteration[-1]

    @property
    def is_first(self) -> bool:
        """
        反回此手势 是否为第一个的布尔值
        用于移动手势位置
        @return:
        """
        return self == self._items_iteration[0]

    @property
    def is_enable(self) -> bool:
        """
        @rtype: bool
        """
        return self.pref.enable and self.enable


class GestureCURE(GestureProperty):
    # TODO
    # def copy(self, from_element):
    #     ...

    def sort(self, is_next):
        gesture = self.pref.gesture
        gl = len(gesture)
        if is_next:
            if self.is_last:
                gesture.move(gl - 1, 0)
                self.index = 0
            else:
                gesture.move(self.index, self.index + 1)
                self.index = self.index + 1
        else:
            if self.is_first:
                gesture.move(self.index, gl - 1)
                self.index = gl - 1
            else:
                gesture.move(self.index - 1, self.index)
                self.index = self.index - 1

    def remove(self):
        self.key_unload()
        if self.is_last and self.index != 0:
            self.index = self.index - 1
        self.pref.gesture.remove(self.index)

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
            self.pref.active_gesture.remove()
            return {"FINISHED"}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, context):
            self.pref.active_gesture.sort(self.is_next)
            return {"FINISHED"}


@cache
def get_element_iteration(gesture: '[Element]') -> [Element]:
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
        layout.prop(self, 'enable', text='')
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
