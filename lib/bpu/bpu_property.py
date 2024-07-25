from bpy.app.translations import pgettext
from mathutils import Vector

from .bpu_type import BPUType


class BpuProperty:
    type: BPUType = BPUType.UNKNOWN  # 类型
    parent: "BpuLayout" = None  # 父级

    __show_separator_line__: bool  # 显示分割线
    __menu_id__: str  # 菜单Id

    level: int = 0  # 绘制的层级

    offset_position: Vector  # 偏移位置
    mouse_position: Vector  # 鼠标位置

    text: str = None  # 绘制的文字 label operator
    font_id: int = 0  # 绘制的文字字体
    font_color = (1, 1, 1, 1)  # 字体颜色
    font_size = -10  # 字体大小

    text_margin = 8  # 文字的间距
    layout_margin = 20  # 布局间距
    __menu_haver__ = dict()  # 菜单的Haver
    __layout_haver__ = list()  # 布局Haver

    active = False  # 是活动项

    def __init__(self):
        self.__clear_children__()
        self.active = False
        self.offset_position = self.mouse_position = Vector((0, 0))

    @property
    def __text__(self):
        """获取绘制的文字"""
        if self.text:
            return self.text
        if self.type.is_operator:
            text = getattr(self, "__operator_text__", "Error")
            if text:
                return pgettext(text, "Operator")
        return "Error"

    @property
    def parent_top(self):
        """反回顶级的父级"""
        if self.parent:
            if self.parent.parent_top:
                return self.parent.parent_top
            else:
                return self.parent
        elif self.type.is_parent:
            return self

    @property
    def __layout_margin_vector__(self) -> Vector:
        """间隔的Vector"""
        return Vector((self.layout_margin, self.layout_margin))

    @property
    def __lmt__(self):
        """间隔"""
        return self.layout_margin * 2

    @property
    def __margin_vector__(self) -> Vector:
        """间隔的Vector"""
        return Vector((self.__margin__, self.__margin__))

    @property
    def __child_margin_vector__(self):
        if self.type.is_menu:
            return self.__layout_margin_vector__
        return self.__margin_vector__

    @property
    def __margin__(self) -> int:
        """间隔"""
        if self.type.is_parent:
            return self.layout_margin
        elif self.type.is_layout:
            if self.parent and self.parent.type.is_parent:
                return 0
            return self.layout_margin
        return self.text_margin

    @property
    def __mt__(self):
        return self.__margin__ * 2

    __draw_children__ = []  # 绘制子级
    __temp_children__ = []  # 添加时的临时子级

    def __clear_children__(self) -> None:
        """清理子级"""
        self.__draw_children__ = []
        self.__temp_children__ = []
        self.__layout_haver__ = []

    @property
    def __children__(self):
        if self.type.is_parent:
            return self.__temp_children__
        else:
            return self.__draw_children__

    @property
    def is_layout(self) -> bool:
        """是layout类型"""
        return self.type.is_layout

    @property
    def is_draw_child(self) -> bool:
        """是可以绘制子级"""
        return self.__children__ and self.type.is_draw_child
