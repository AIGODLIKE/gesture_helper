import math
import re
from functools import cache

import blf
import gpu
from mathutils import Vector

from ..utils.public import get_pref
from ..utils.public_gpu import PublicGpu

pattern = re.compile(r'[\u4e00-\u9fa5]')


@cache
def check_china(text):
    return bool(pattern.findall(text))


@cache
def from_text_get_dimensions(text, size):
    font_id = 0
    blf.size(font_id, size)
    dimensions = blf.dimensions(font_id, text)
    return dimensions


@cache
def get_position(direction, radius):
    angle = math.radians((int(direction) - 1) * 45)  # 将角度转换为弧度
    return Vector((radius * math.cos(angle), radius * math.sin(angle)))


class ElementGpuProperty:

    @property
    def text_size(self):
        return self.draw_property.text_gpu_draw_size

    @property
    def text_margin(self):
        return self.draw_property.text_gpu_draw_margin

    @property
    def text_radius(self):
        return self.draw_property.text_gpu_draw_radius

    @property
    def text_dimensions(self) -> tuple:
        return from_text_get_dimensions(self.text, self.text_size)

    @property
    def text(self) -> str:
        return self.name

    @property
    def is_active_direction(self):
        distance_ok = self.ops.distance > self.gesture_property.threshold * 0.7
        return self == self.ops.direction_element and distance_ok

    @property
    def draw_color(self):
        draw = self.draw_property
        return draw.text_active_color if self.is_active_direction else draw.text_default_color

    @property
    def rounded_rectangle_color(self):
        draw = self.draw_property
        return draw.background_active_color if self.is_active_direction else draw.background_default_color


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
            direction = self.direction
            offset = [0, 0]

            if direction == '1':
                offset = (0, hh)
            elif direction == '2':
                offset = (0, h)
            elif direction == '3':
                offset = (-hw, h * 2)
            elif direction == '4':
                offset = (-w, h)
            elif direction == '5':
                offset = (-w + 0.2, hh)
            elif direction == '6':
                offset = (-w, -hh / 2)
            elif direction == '7':
                offset = (-hw, -h)
            elif direction == '8':
                offset = (0, -hh / 2)

            margin = self.text_margin  # px
            rounded_rectangle = {
                "radius": self.text_radius,
                "position": (0, 0),
                "width": w + margin * 2,
                "height": h + margin * 2,
                "color": self.rounded_rectangle_color
            }
            gpu.matrix.translate(offset)
            with gpu.matrix.push_pop():
                x, y = hw, -h
                y *= 0.7

                gpu.matrix.translate([x, y])
                self.draw_rounded_rectangle_area(**rounded_rectangle)
                self.draw_rounded_rectangle_frame(**{**rounded_rectangle, "color": (0.3, 0.3, 0.4, 1)})
            self.draw_text((0, 0), self.text, color=self.draw_color, size=self.text_size)
