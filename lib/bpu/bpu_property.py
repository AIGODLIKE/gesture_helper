import blf
from mathutils import Vector

from .bpu_type import BPUType


class BpuProperty:
    margins = 2  # 边距

    type: BPUType = BPUType.UNKNOWN  # 类型

    level: int = 0  # 绘制的层级

    mouse_position: Vector  # 鼠标位置

    text: str = ""  # 绘制的文字 label operator
    font_id: int = 0  # 绘制的文字字体

    children = []  # 子级,不需要父级
    _temp_children = []  # 临时子级,在更新时使用

    # in_updating: bool = False  # 正在更新中
    __measure_res__ = None  # 测量结果

    @property
    def __margins_vector__(self):
        if self.type.is_horizontal_layout:
            return Vector((self.margins, 0))
        elif self.type.is_vertical_layout:
            return Vector((0, self.margins))
        else:
            return Vector((self.margins, self.margins))

    @property
    def __measure__(self) -> Vector:
        """测量数据"""
        if self.__measure_res__ is not None:
            return self.__measure_res__

        if self.type.is_draw_text:
            td = blf.dimensions(self.font_id, self.text)
            self.__measure_res__ = Vector([td[0], td[1]]) + self.__margins_vector__
        elif self.type.is_layout:
            measure = Vector([0, 0])
            for child in self.children:
                measure += child.__measure__
            self.__measure_res__ = measure + self.__margins_vector__
        return self.__measure_res__

    @property
    def is_layout(self):
        return self.type.is_layout
