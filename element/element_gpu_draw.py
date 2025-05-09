import math
import re
from functools import cache

import blf
import bpy
import gpu
from bl_operators.wm import context_path_validate
from mathutils import Vector

from ..utils.public import get_pref
from ..utils.public_gpu import PublicGpu
from ..utils.texture import Texture

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
        scale = bpy.context.preferences.view.ui_scale
        return self.draw_property.text_gpu_draw_size * scale

    @property
    def text_margin(self):
        scale = bpy.context.preferences.view.ui_scale
        return self.draw_property.text_gpu_draw_margin * scale

    @property
    def text_radius(self):
        scale = bpy.context.preferences.view.ui_scale
        return self.draw_property.text_gpu_draw_radius * scale

    @property
    def text_dimensions(self) -> tuple:
        return from_text_get_dimensions(self.text, self.text_size)

    @property
    def text(self) -> str:
        return self.name_translate

    @property
    def is_active_direction(self):
        distance_ok = self.ops.distance > self.gesture_property.threshold * 0.7
        return self == self.ops.direction_element and distance_ok

    @property
    def is_draw_property_bool(self) -> bool:
        is_ops = self.operator_bl_idname == 'wm.context_toggle'
        is_operator_type = self.operator_type == "OPERATOR"
        data = self.properties
        if not self.is_operator or not is_operator_type:
            # 不是操作符或是脚本运行
            return False
        elif not is_ops:
            return False
        elif 'data_path' not in data:
            return False
        elif self.get_operator_wm_context_toggle_property_bool is Ellipsis:
            return False
        return True

    @property
    def get_operator_wm_context_toggle_property_bool(self) -> [bool]:
        """获取操作符 wm.context_toggle 的布尔值"""
        if 'data_path' in self.properties:
            return context_path_validate(bpy.context, self.properties['data_path'])
        return False

    @property
    def text_color(self):
        """
        文字颜色
        :return:
        """
        draw = self.draw_property
        return draw.text_active_color if self.is_active_direction else draw.text_default_color

    @property
    def background_color(self):
        """
        背景颜色
        :return:
        """
        draw = self.draw_property
        if self.is_active_direction:
            if self.is_operator:
                return draw.background_operator_active_color
            elif self.is_child_gesture:
                return draw.background_child_active_color
        elif self.is_operator:
            if self.operator_type == "OPERATOR":
                if self.is_draw_property_bool:
                    if self.get_operator_wm_context_toggle_property_bool:
                        return draw.background_bool_true
                    else:
                        return draw.background_bool_false
            return draw.background_operator_color
        elif self.is_child_gesture:
            return draw.background_child_color


class ElementGpuDraw(PublicGpu, ElementGpuProperty):
    def draw_gpu_item(self, ops):
        self.ops = ops
        scale = bpy.context.preferences.view.ui_scale

        radius = get_pref().gesture_property.radius * scale
        position = get_position(self.direction, radius)

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)

            w, h = self.text_dimensions
            hh = h / 2
            hw = w / 2
            direction = self.direction
            offset = [0, 0]
            icon_size = h * 1.3

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
            width = w + margin * 2
            height = h + margin * 2

            if self.is_draw_icon:
                width += icon_size

            hh = height / 2
            rounded_rectangle = {
                "radius": self.text_radius if (hh > self.text_radius) else height,
                "position": (0, 0),
                "width": width,
                "height": height,
                "color": self.background_color
            }
            gpu.matrix.translate(offset)
            with gpu.matrix.push_pop():
                x, y = hw, -h
                y *= 0.7

                gpu.matrix.translate([x, y])
                self.draw_rounded_rectangle_area(**rounded_rectangle)

            with gpu.matrix.push_pop():
                if self.is_draw_icon:
                    gpu.matrix.translate([-(icon_size * 0.6), 0])
                    gpu.state.blend_set('ALPHA_PREMULT')
                    gpu.state.depth_test_set('ALWAYS')
                    self.draw_image([0, -(h * 1.3)], icon_size, icon_size, texture=Texture.get_texture(self.icon))
                    gpu.matrix.translate([icon_size * 1.2, icon_size])

                self.draw_text([0, 0], self.text, color=self.text_color, size=self.text_size)
