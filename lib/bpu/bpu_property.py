from mathutils import Vector

from .bpu_type import BPUType, Quadrant


class BpuProperty:
    type: BPUType = BPUType.UNKNOWN  # 类型

    level: int = 0  # 绘制的层级

    mouse_position: Vector  # 鼠标位置

    text: str = ""  # 绘制的文字 label operator
    font_id: int = 0  # 绘制的文字字体
    font_color = (1, 1, 1, 1)  # 字体颜色
    font_size = 24

    text_margin = 10
    layout_margin = 50

    @property
    def __margin_vector__(self) -> Vector:
        return Vector([self.__margin__, self.__margin__])

    @property
    def __margin__(self) -> int:
        if self.type.is_layout:
            return self.layout_margin
        return self.text_margin

    __draw_children__ = []  # 绘制子级
    __temp_children__ = []  # 添加时的临时子级

    is_invert: bool = False  # 是反转

    def __clear_children__(self) -> None:
        self.__draw_children__ = []
        self.__temp_children__ = []

    def __init__(self):
        self.font_size = 24
        self.__clear_children__()

    @property
    def is_layout(self) -> bool:
        return self.type.is_layout

    @property
    def is_draw_child(self) -> bool:
        return self.__draw_children__ and self.type.is_draw_child

    @property
    def draw_children(self) -> list["BpuProperty"]:
        """绘制子级时需判断是否反转
        """
        if self.is_invert:
            return self.__draw_children__
        return self.__draw_children__[::-1]
