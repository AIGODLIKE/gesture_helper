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

    __temp_children__ = []  # 添加时的临时子级
    __draw_children__ = []  # 绘制子级

    __measure_res__ = None  # 测量结果

    is_invert = False  # 是反转

    @property
    def __margins_vector__(self):
        if self.type.is_horizontal_layout:
            return Vector((self.margins, 0))
        elif self.type.is_vertical_layout:
            return Vector((0, self.margins))
        else:
            return Vector((self.margins, self.margins))

    def __measure_vector__(self, parent_layout):
        measure = self.__measure__
        if parent_layout.type.is_horizontal_layout:
            return Vector((measure[0], 0))
        elif parent_layout.type.is_vertical_layout:
            return Vector((0, measure[1]))
        else:
            return Vector(measure)

    @property
    def __measure__(self) -> Vector:
        """测量数据"""
        if self.__measure_res__ is not None:
            return self.__measure_res__

        if self.type.is_draw_text:
            td = blf.dimensions(self.font_id, self.text)
            self.__measure_res__ = Vector([td[0], td[1]]) + self.__margins_vector__
        elif self.type.is_draw_child:
            measure = Vector([0, 0])
            for child in self.__temp_children__:
                measure += child.__measure__
            self.__measure_res__ = measure + self.__margins_vector__
        return self.__measure_res__

    @property
    def is_layout(self):
        return self.type.is_layout

    @property
    def is_draw_child(self):
        return self.__draw_children__ and self.type.is_draw_child

    @property
    def draw_children(self):
        """绘制子级时需判断是否反转
        """
        if self.is_invert:
            return self.__draw_children__
        return self.__draw_children__[::-1]
