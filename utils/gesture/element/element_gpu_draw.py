import math

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
    def is_active_direction(self):
        ...

    @property
    def draw_color(self):
        return (1, 1, 1, 1)


class ElementGpuDraw(PublicGpu, ElementGpuProperty):
    def draw_gpu_item(self, ops):
        self.ops = ops
        if ops.is_draw_gpu:
            self.draw_gpu_text()
            self.draw_gpu_box()

    def draw_gpu_text(self):
        self.draw_text(self.draw_position, self.name)

    def draw_gpu_box(self):
        ...
