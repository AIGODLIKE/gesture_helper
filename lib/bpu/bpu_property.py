import blf
from mathutils import Vector

from .bpu_type import BPUType


class BpuProperty:
    margins = 2  # 边距

    type: BPUType  # 类型

    level: int  # 绘制的层级

    mouse_position: Vector  # 鼠标位置

    text: str  # 绘制的文字 label operator
    font_id: int  # 绘制的文字字体

    children = []  # 子级,不需要父级
    _temp_children = []  # 临时子级,在更新时使用

    # in_updating: bool = False  # 正在更新中
    __is_measure__ = False  # 已测量

    @property
    def __margins_vector__(self):
        return Vector([self.margins, self.margins])

    @property
    def __measure__(self) -> Vector:
        """测量数据"""
        if self.type.is_draw_text:
            self.__is_measure__ = True
            td = blf.dimensions(fontid=self.font_id, text=self.text)
            return Vector([td[0], td[1]]) + self.__margins_vector__
        elif self.type.is_layout:
            measure = Vector([0, 0])
            for child in self.children:
                measure += child.__measure__()
            self.__is_measure__ = True
            return measure + self.__margins_vector__

    @property
    def is_layout(self):
        return self.type.is_layout

    def __init__(self):
        self.type = BPUType.UNKNOWN
        self.level = 0
        self.font_id = 0
