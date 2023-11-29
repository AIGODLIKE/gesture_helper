import math
from functools import cache

import blf
import gpu
from mathutils import Vector

from ...public import get_pref
from ...public_gpu import PublicGpu


@cache
def from_text_get_dimensions(text):
    dimensions = blf.dimensions(0, text)
    return dimensions


@cache
def get_direction(direction):
    # 方向的步数
    from ...public import DIRECTION_STOP_DICT
    for k, v in DIRECTION_STOP_DICT.items():
        if k == direction:
            return int(v)


@cache
def get_position(direction, radius):
    direction_stop = get_direction(direction)
    angle = math.radians((direction_stop - 1) * 45)  # 将角度转换为弧度
    return Vector((radius * math.cos(angle), radius * math.sin(angle)))


class ElementGpuProperty:

    @property
    def text_dimensions(self) -> tuple:
        return from_text_get_dimensions(self.text)

    @property
    def text(self) -> str:
        return self.name

    @property
    def is_active_direction(self):
        distance_ok = self.ops.distance > self.gesture_property.threshold * 0.7
        return self == self.ops.direction_element and distance_ok

    @property
    def draw_color(self):
        return (0, 0, 0, 1) if self.is_active_direction else (1, 1, 1, 1)


class ElementGpuDraw(PublicGpu, ElementGpuProperty):
    def draw_gpu_item(self, ops):
        self.ops = ops
        radius = get_pref().gesture_property.radius
        position = get_position(self.direction, radius)

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)

            w, h = self.text_dimensions
            hh = h / 2
            hw = w / 2
            margin = 10  # px
            direction = self.direction
            rro = offset = [0, 0]

            if direction == '1':
                offset = (-w + 0.2, h)
                rro = (hw + margin / 2, -hh)
            elif direction == '2':
                offset = (0, h)
                rro = (0, h)
            elif direction == '3':
                offset = (-hw, -h)
            elif direction == '4':
                offset = (-hw, h * 2)
            elif direction == '5':
                offset = (-w, h)
            elif direction == '6':
                offset = (0, h)
            elif direction == '7':
                offset = (-w, -hh / 2)
            elif direction == '8':
                offset = (0, -hh / 2)

            rounded_rectangle = {
                "radius": 5,
                "position": (0, 0),
                "width": w + margin * 2,
                "height": h + margin * 2,
                "color": (0.5, 0.5, 0.5, 1)
            }
            gpu.matrix.translate(offset)
            with gpu.matrix.push_pop():
                gpu.matrix.translate(rro)
                self.draw_rounded_rectangle_frame(**rounded_rectangle)
                self.draw_rounded_rectangle_area(**rounded_rectangle)
            self.draw_text((0, 0), self.text, color=self.draw_color)
