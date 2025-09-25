import math
from functools import cache

import blf
import bpy
import gpu
import numpy as np
from bl_operators.wm import context_path_validate
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector

from ..utils import including_chinese, has_special_characters
from ..utils.color import linear_to_srgb
from ..utils.gpu import get_now_2d_offset_position
from ..utils.public import get_pref, get_gesture_extension_items
from ..utils.public_gpu import PublicGpu
from ..utils.texture import Texture


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
        return [i * scale for i in self.draw_property.text_gpu_draw_margin]

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
        if self.is_active_direction and not self.ops.mouse_is_in_extension_any_area:
            if self.is_operator:
                return draw.background_operator_active_color
            elif self.is_child_gesture:
                return draw.background_child_active_color
        if self.is_operator:
            if self.operator_type == "OPERATOR":
                if self.is_draw_property_bool:
                    if self.get_operator_wm_context_toggle_property_bool:
                        return draw.background_bool_true
                    else:
                        return draw.background_bool_false
            return draw.background_operator_color
        if self.is_child_gesture:
            return draw.background_child_color
        return 1, 0, 0, 1

    @property
    def extension_background_color(self):
        draw = self.draw_property
        if self.extension_by_child_is_hover or self in self.ops.extension_hover:
            return draw.background_child_active_color
        return draw.background_child_color


class ElementGpuDraw(PublicGpu, ElementGpuProperty):

    @property
    def extension_items(self) -> dict['GestureElement']:
        """
        扩展项 就是底部
        :return:
        """
        return get_gesture_extension_items(self.element)

    def draw_gpu_item(self, ops):
        """
        布局

        4 3 2
        5   1
        6 7 8
          9
        """
        self.ops = ops

        direction = self.direction
        if direction == '9':
            scale = bpy.context.preferences.view.ui_scale
            pref = get_pref()
            radius = pref.gesture_property.radius * scale
            position = get_position("7", radius)
            with gpu.matrix.push_pop():
                gpu.matrix.translate(position)
                draw_debug_point((1, 1, 0, 1), 2)

                if "7" in self.ops.direction_items.keys():
                    gpu.matrix.translate(self.draw_direction_offset)
                else:
                    gpu.matrix.translate((0, -self.max_height_dimensions))
                w, h = self.extension_dimensions

                draw_debug_point((1, 0, 0, 1))
                self.extension_offset_start_position = get_now_2d_offset_position()
                gpu.matrix.translate((-w / 2, 0))
                self.draw_gpu_extension_item(ops)
            return
        scale = bpy.context.preferences.view.ui_scale

        radius = get_pref().gesture_property.radius * scale
        position = get_position(self.direction, radius)

        margin_x, margin_y = self.draw_property.text_gpu_draw_margin

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)

            w, h = self.draw_dimensions
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.draw_direction_offset)
                self.gpu_draw_margin()
                x, y = get_now_2d_offset_position()
                self.gpu_draw_icon()
                self.gpu_draw_text_fix_offset()
                self.gpu_draw_child_icon()

                self.item_draw_area = [x - margin_x, y - h - margin_y, x + w + margin_x, y + margin_y]

    def gpu_draw_text_fix_offset(self, use_offset=True, fix_offset=True):
        """通过对每种不同的文字偏移实现绘制位置正确"""
        with gpu.matrix.push_pop():
            w, h = self.text_dimensions
            text = self.text
            special_characters = has_special_characters(text)
            if including_chinese(text):  # 中文
                offset = [0, h * 0.158]
            elif "_" in text and not special_characters:  # 有下划线在文字内
                offset = [0, h * 0.325]
            elif has_special_characters(text):  # 特殊字符
                offset = [0, h * 0.1]
            else:  # 只有英文
                offset = [0, h * 0.355]
            if fix_offset:
                gpu.matrix.translate(offset)
            self.draw_text(text, position=[0, 0], color=self.text_color, size=self.text_size, auto_offset=False)
        if use_offset:
            gpu.matrix.translate((w, 0))

    def gpu_draw_icon(self, use_offset=True):
        w, h = self.text_dimensions
        if self.is_draw_property_bool and getattr(self, "extension_icon_size", None):
            h = self.extension_icon_size
        if self.is_draw_icon:
            icon = self.icon
            if self.is_draw_property_bool:
                if self.get_operator_wm_context_toggle_property_bool:
                    icon = "CHECKBOX_HLT"
                else:
                    icon = "CHECKBOX_DEHLT"
            self.draw_image([0, -h], h, h, texture=Texture.get_texture(icon))
            if use_offset:
                gpu.matrix.translate((self.icon_offset_width, 0))

    def gpu_draw_child_icon(self, use_offset=True):
        w, h = self.text_dimensions
        if self.is_draw_child_icon:
            self.draw_image([0, -h], h, h, texture=Texture.get_texture("1"))
            if use_offset:
                gpu.matrix.translate((self.icon_offset_width, 0))

    def gpu_draw_margin(self):
        w, h = self.draw_dimensions
        wm, hm = self.text_margin
        with gpu.matrix.push_pop():
            gpu.matrix.translate((w / 2, -h / 2))
            draw_debug_point()

            radius = self.text_radius if (h / 2 > self.text_radius) else h / 2

            rounded_rectangle = {
                "radius": radius,
                "position": (0, 0),
                "width": w + wm * 2,
                "height": h + hm * 2,
                "color": linear_to_srgb(np.array(self.background_color, dtype=np.float32)),
            }
            self.draw_rounded_rectangle_area(**rounded_rectangle)

    icon_interval = .5

    @property
    def icon_offset_width(self) -> float:
        w, h = self.text_dimensions
        return h + h * self.icon_interval

    @property
    def draw_dimensions(self) -> Vector:
        w, h = self.text_dimensions
        if self.is_draw_icon:
            w += self.icon_offset_width
        if self.is_draw_child_icon:
            w += self.icon_offset_width
        return Vector((w, h))

    @property
    def draw_direction_offset(self) -> Vector:
        w, h = self.draw_dimensions
        hb = h / 2  # bisect
        wb = w / 2
        offset = [0, 0]
        direction = self.direction
        if direction == '1':
            offset = (0, hb)
        elif direction == '2':
            offset = (0, h)
        elif direction == '3':
            offset = (-wb, h * 2)
        elif direction == '4':
            offset = (-w, h)
        elif direction == '5':
            offset = (-w, hb)
        elif direction == '6':
            offset = (-w, 0)
        elif direction == '7':
            offset = (-wb, -h)
        elif direction == '8':
            offset = (0, 0)
        elif direction == '9':
            offset = (0, -h * get_pref().draw_property.element_extension_item_offset)
        return Vector(offset)


class ElementGpuExtensionItem:
    extension_interval = .4

    @property
    def dividing_line_height(self) -> float:
        dividing_line_height = self.draw_property.dividing_line_height
        scale = bpy.context.preferences.view.ui_scale
        return dividing_line_height * scale

    @property
    def max_height_dimensions(self) -> float:
        return max((0, *(item.text_dimensions[1] for item in self.extension_items if not item.is_dividing_line)))

    @property
    def max_width_dimensions(self) -> float:
        return max((0, *(item.text_dimensions[0] for item in self.extension_items if not item.is_dividing_line)))

    @property
    def max_dimensions(self) -> Vector:
        return Vector((self.max_width_dimensions, self.max_height_dimensions))

    @property
    def extension_dimensions(self) -> Vector:
        interval = self.extension_interval

        max_height = self.max_height_dimensions
        max_width = self.max_width_dimensions
        h = 0
        w = max_width
        for item in self.extension_items:
            if item.is_dividing_line:
                h += self.dividing_line_height + max_height * interval
            else:
                h += max_height + max_height * interval

        self.extension_icon_size = max_height
        self.extension_icon_interval = max_height * interval
        self.extension_text_width = max_width
        w += max_height * 2 + self.extension_icon_interval
        return Vector((w, h))

    def draw_gpu_extension_item(self, ops):
        w, h = self.extension_dimensions
        margin_x, margin_y = self.draw_property.text_gpu_draw_margin
        with gpu.matrix.push_pop():
            if self not in ops.extension_hover:
                ops.extension_hover.append(self)
            draw_debug_point()
            self.draw_gpu_extension_margin()

            for item in self.extension_items:
                item.ops = ops
                wi, hi = self.max_dimensions

                if item.is_dividing_line:
                    # 活动项颜色
                    color = linear_to_srgb(np.array(self.draw_property.dividing_line_color, dtype=np.float32))
                    hs = self.dividing_line_height / 2
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((w / 2, -(self.dividing_line_height + self.extension_icon_interval / 2)))
                        rounded_rectangle = {
                            "radius": hs,
                            "position": (0, 0),
                            "width": w,
                            "height": self.dividing_line_height,
                            "color": color,
                        }
                        self.draw_rounded_rectangle_area(**rounded_rectangle)
                    gpu.matrix.translate((0, -(self.dividing_line_height + self.extension_icon_interval)))
                else:
                    if item.extension_by_child_is_hover:
                        color = linear_to_srgb(np.array(item.extension_background_color, dtype=np.float32))
                        dh = hi + hi * self.extension_interval
                        rounded_rectangle = {
                            "radius": self.text_radius,
                            "position": (w / 2, -dh / 2),
                            "width": w + margin_x,
                            "height": dh,
                            "color": color,
                        }
                        self.draw_rounded_rectangle_area(**rounded_rectangle)

                    with gpu.matrix.push_pop():
                        s = self.extension_icon_size
                        gpu.matrix.translate((0, -(hi * self.extension_interval) / 2))
                        if item.is_draw_icon:
                            item.gpu_draw_icon(False)
                        gpu.matrix.translate((self.extension_icon_size + self.extension_icon_interval, 0))
                        item.gpu_draw_text_fix_offset(use_offset=False, fix_offset=True)
                        gpu.matrix.translate((self.extension_text_width, 0))
                        if item.is_child_gesture:
                            self.draw_image([0, -s], s, s, texture=Texture.get_texture("1"))
                        gpu.matrix.translate((self.extension_icon_size, 0))

                        if item.is_child_gesture and (item.extension_by_child_is_hover or item in ops.extension_hover):
                            gpu.matrix.translate((margin_x * 1.9, 0))
                            item.draw_gpu_extension_item(ops)
                        draw_debug_point()
                        ex, ey = get_now_2d_offset_position()

                    gpu.matrix.translate((0,
                                          -(self.extension_icon_size + self.extension_icon_interval)
                                          ))

                    draw_debug_point()
                sx, sy = get_now_2d_offset_position()
                hs = (hi * self.extension_interval) / 2
                item.extension_by_child_draw_area = [sx, sy, ex, ey + hs]

            if len(self.extension_items) == 0:
                self.draw_text(
                    bpy.app.translations.pgettext_iface("No child level, please add"),
                    size=self.text_size,
                    position=[0, 0])

    def draw_gpu_extension_margin(self):
        draw = self.draw_property

        margin_x, margin_y = self.draw_property.text_gpu_draw_margin

        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        w, h = self.extension_dimensions
        x, y = get_now_2d_offset_position()
        self.extension_draw_area = [x - margin_x, y - h - margin_y, x + w + margin_x, y + margin_x]

        if len(self.extension_items) == 0:
            return
        rounded_rectangle = {
            "radius": self.text_radius,
            "position": (w / 2, -h / 2),
            "width": w + margin_x * 2,
            "height": h + margin_y * 2,
            "color": linear_to_srgb(np.array(draw.background_child_color, dtype=np.float32)),
        }
        self.draw_rounded_rectangle_area(**rounded_rectangle)


def draw_debug_point(color=(0, 1, 1, 1), radius=1):
    if get_pref().debug_property.debug_extension:
        draw_circle_2d([0, 0], color, radius)
