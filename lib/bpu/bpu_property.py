from mathutils import Vector

from .bpu_type import BPUType


class BpuProperty:
    _draw_x: int  # 绘制的起始X位置
    _draw_y: int  # 绘制的起始Y位置

    _width: int  # 绘制的宽度
    _height: int  # 绘制的高度

    _type: BPUType

    mouse_position: Vector

