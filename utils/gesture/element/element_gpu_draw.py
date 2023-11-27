import math

import blf
import gpu
from mathutils import Vector

from ...public_gpu import PublicGpu


class ElementGpuProperty:
    __gesture_angle_step__ = 360 / 8  # 每一段的角度

    @property
    def direction_stop(self) -> int:  # 方向的步数
        from ...public import DIRECTION_STOP_DICT
        for k, v in DIRECTION_STOP_DICT.items():
            if k == self.direction:
                return int(v)

    @property
    def draw_position(self) -> (int, int):
        radius = self.pref.gesture_property.radius
        angle = math.radians((self.direction_stop - 1) * self.__gesture_angle_step__)  # 将角度转换为弧度
        x, y = self.ops.last_region_position
        return Vector((x + radius * math.cos(angle), y + radius * math.sin(angle)))

    @property
    def text_dimensions(self) -> tuple:
        return blf.dimensions(0, self.text)

    @property
    def text(self) -> str:
        return self.name

    @property
    def is_active_direction(self):
        return self == self.ops.direction_element

    @property
    def draw_color(self):
        return (0, 0, 0, 1) if self.is_active_direction else (1, 1, 1, 1)


class ElementGpuDraw(PublicGpu, ElementGpuProperty):
    def draw_gpu_item(self, ops):
        self.ops = ops
        if ops.is_draw_gpu:
            with gpu.matrix.push_pop():
                x, y = self.draw_position
                w, h = self.text_dimensions
                hh = h / 2
                hw = w / 2
                margin = 5  # px
                direction = self.direction
                offset = (0, 0)
                text_offset = (0, 0)
                rounded_rectangle_offset = (0, 0)
                if direction == '1':
                    offset = (x - w, y + h)
                    text_offset = -margin, 0
                    rounded_rectangle_offset = hw, -hh
                elif direction == '2':
                    offset = (x, y + h)
                    text_offset = margin, 0
                    rounded_rectangle_offset = hw, -hh
                elif direction == '3':
                    offset = (x - hw, y - h)
                    text_offset = 0, -margin
                    rounded_rectangle_offset = -hw, -hh
                elif direction == '4':
                    offset = (x - hw, y + h + h)
                    text_offset = 0, margin
                    rounded_rectangle_offset = hw, -hh
                elif direction == '5':
                    offset = (x - w, y + h)
                    text_offset = -margin, margin
                    rounded_rectangle_offset = hw, -hh
                elif direction == '6':
                    offset = (x, y + h)
                    text_offset = margin, margin
                    rounded_rectangle_offset = hw, -hh
                elif direction == '7':
                    offset = (x - w, y - (hh / 2))
                    text_offset = -margin, -margin
                    rounded_rectangle_offset = hw, -hh
                elif direction == '8':
                    offset = (x, y - (hh / 2))
                    text_offset = margin, -margin
                    rounded_rectangle_offset = hw, -hh
                gpu.matrix.translate(offset)
                rounded_rectangle = {
                    "radius": 5,
                    "position": (0, 0),
                    "width": w + margin,
                    "height": h + margin,
                    "color": (0.5, 0.5, 0.5, 1)
                }
                # with gpu.matrix.push_pop():
                #     gpu.matrix.translate(rounded_rectangle_offset)
                #     self.draw_rounded_rectangle_frame(**rounded_rectangle)
                #     self.draw_rounded_rectangle_area(**rounded_rectangle)
                with gpu.matrix.push_pop():
                    gpu.matrix.translate(text_offset)
                    self.draw_text((0, 0), self.text, color=self.draw_color)
                # self.draw_2d_rectangle(0, 0, 20, -10)
