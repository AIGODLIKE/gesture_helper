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
    item_position: Vector  # 偏移位置
    mouse_position: Vector  # 鼠标位置

    text: str = None  # 绘制的文字 label operator
    font_id: int = 0  # 绘制的文字字体
    font_color = (1, 1, 1, 1)  # 字体颜色
    font_size = 24  # 字体大小

    text_margin = 15  # 文字的间距
    layout_margin = 10  # 布局间距
    __haver_map__ = dict()

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

    @property
    def __margin_vector__(self) -> Vector:
        """间隔的Vector"""
        return Vector([self.__margin__, self.__margin__])

    @property
    def __margin__(self) -> int:
        """间隔"""
        if self.type.is_layout:
            return self.layout_margin
        return self.text_margin
    @property
    def __mt__(self):
        return self.__margin__ *2

    __draw_children__ = []  # 绘制子级
    __temp_children__ = []  # 添加时的临时子级

    is_invert: bool = False  # 是反转

    def __clear_children__(self) -> None:
        """清理子级"""
        self.__draw_children__ = []
        self.__temp_children__ = []

    def __init__(self):
        self.__clear_children__()

        self.font_size = 24
        self.mouse_position = self.item_position = self.offset_position = Vector([-1, -1])

    @property
    def is_layout(self) -> bool:
        """是layout类型"""
        return self.type.is_layout

    @property
    def is_draw_child(self) -> bool:
        """是可以绘制子级"""
        return self.__draw_children__ and self.type.is_draw_child

    @property
    def draw_children(self) -> list["BpuLayout"]:
        """反回绘制子级列表
        绘制子级时需判断是否反转

        从上向下绘制"""
        if self.is_invert:
            return self.__draw_children__
        return self.__draw_children__[::-1]
