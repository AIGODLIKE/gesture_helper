from mathutils import Vector

from .bpu_type import BPUType


class BpuProperty:
    _draw_x: int  # 绘制的起始X位置
    _draw_y: int  # 绘制的起始Y位置

    _width: int  # 绘制的宽度
    _height: int  # 绘制的高度

    _type: BPUType  # 类型

    level: int  # 绘制的层级

    mouse_position: Vector  # 鼠标位置

    text: str  # 绘制的文字 label operator
    font_id: int  # 绘制的文字字体

    @property
    def is_layout(self):
        return self._type.is_layout

    def __init__(self):
        self._type = BPUType.UNKNOWN
        self.level = 0
        self.font_id = 0
