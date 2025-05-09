import re

import blf
import bpy
import gpu
from mathutils import Vector

from .bpu_debug import BpuDebug
from .bpu_prop_layout import BpuPropLayout
from ....utils.public_gpu import PublicGpu


def __box_path__(width: int, height: int) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
    return [0, 0], [0, height], [width, height], [width, 0], [0, 0]


def contains_chinese(text):
    pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(pattern.search(text))


IS_DEBUG_DRAW: bool = False  # 绘制
IS_DEBUG_INFO: bool = False  # 绘制左下角信息
IS_DEBUG_HAVER: bool = False  # 绘制是否为Haver
IS_DEBUG_POINT: bool = False  # 绘制线POINT


class BpuDraw(BpuPropLayout, PublicGpu, BpuDebug):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __gpu_draw__(self):
        """gpu绘制主方法"""
        if IS_DEBUG_DRAW:
            # print("__gpu_draw__\n")
            ...

        area = bpy.context.region
        self.__measure__()
        self.__layout_haver__ = list()
        with gpu.matrix.push_pop():
            gpu.matrix.translate([-area.x, -area.y])
            gpu.matrix.translate(self.offset_position)

            if IS_DEBUG_INFO:
                self.draw_2d_points(Vector((0, 0)), color=(1, 0, 0, 0.3), point_size=50)

            gpu.matrix.translate(self.__quadrant_translate__)
            self.__layout__()

            if IS_DEBUG_INFO:
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((-500, 100))
                    for index, i in enumerate((
                            getattr(bpy.context, "button_pointer", None),
                            getattr(bpy.context, "button_prop", None),
                            getattr(bpy.context, "button_operator", None),
                            str(bpy.context.area.type),
                            str(self.offset_position),
                            str(self.mouse_position),
                            str(self.__active_operator__),
                            f"haver:{self.__menu_haver__}",
                            f"{self.__layout_haver__}",)
                    ):
                        self.draw_text([0, 50 + -50 * index], text=i, font_id=self.font_id)
        self.__layout_haver_histories__ = self.__layout_haver__

    def __layout__(self) -> None:
        """
        先测量宽高
        然后绘制子级
        """
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        if self.type.is_parent:
            self.__draw_layout__()
        elif self.type.is_separator:
            self.__draw_separator__()
        elif self.type.is_menu:
            self.__draw_menu__()
        elif self.type.is_layout:
            self.__draw_layout__()
        elif self.type.is_draw_item:
            self.__draw_item__()
        elif self.type.is_prop:
            self.__draw_property__()

        self.__draw_debug__()
        if self.is_draw_child:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__child_margin_vector__)
                self.__draw_child__()
            self.__draw_haver_position_debug__()
        self.check_haver()

    def __draw_separator__(self, factor=0.95):
        """绘制分隔符"""
        parent = self.parent
        with gpu.matrix.push_pop():
            pt = parent.type
            if pt.is_horizontal_layout:
                vs = [Vector((0, 0)), Vector((0, parent.__child_max_height__ * factor))]
                gpu.matrix.translate((0, parent.__child_max_height__ * (1 - factor) / 2))
            elif pt.is_vertical_layout or pt.is_parent:
                vs = [Vector((0, 0)), Vector((parent.__child_max_width__ * factor, 0))]
                gpu.matrix.translate((parent.__child_max_width__ * (1 - factor) / 2, 0))
            else:
                Exception(f"Error parent Not match :{parent.type}")
            if pt.is_horizontal_layout:
                gpu.matrix.translate((self.__draw_width__ / 2, 0))
            elif pt.is_vertical_layout or pt.is_parent:
                gpu.matrix.translate((0, self.__draw_height__ / 2))

            self.draw_2d_line(vs, color=self.__separator_color__, line_width=2)
        self.__draw_haver_position_debug__()

    def __draw_item__(self) -> None:
        """绘制项"""
        if IS_DEBUG_DRAW:
            if self.type.is_prop:
                ...
            else:
                self.draw_2d_line(
                    self.__margin_box__,
                    color=self.__debug_item_margin_color__,
                    line_width=self.__debug_line__
                )
        self.__draw_active__()
        self.__draw_haver__()
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.__margin_vector__)
            if IS_DEBUG_DRAW:
                self.draw_2d_line(
                    self.__bound_box__,
                    color=self.__debug_item_bound_color__,
                    line_width=self.__debug_line__)

            if contains_chinese(self.__text__):
                pt = self.parent.type
                if pt.is_vertical_layout or pt.is_parent or pt.is_menu:
                    gpu.matrix.translate(Vector([0, self.__text_height__ * 0.1]))

            font_id = self.font_id
            blf.position(font_id, 0, 0, self.level)
            blf.color(font_id, *self.___text_color___)
            blf.size(font_id, self.font_size)
            blf.draw(font_id, self.__text__)
        if not self.type.is_prop:
            self.__draw_haver_position_debug__()

    def __draw_layout__(self) -> None:
        """绘制layout"""
        with gpu.matrix.push_pop():
            gpu.matrix.translate((self.__draw_width__ / 2, self.__draw_height__ / 2))
            self.draw_rounded_rectangle_area(
                [0, 0],
                radius=self.__layout_radius__,
                color=self.__background_normal_color__,
                width=self.__draw_width__,
                height=self.__draw_height__,
                segments=self.__layout_segments__)
        if IS_DEBUG_DRAW:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.parent_offset())
                self.draw_2d_line(
                    self.__bound_box__,
                    color=self.__debug_layout_margin_color__,
                    line_width=self.__debug_line__)
            self.draw_2d_line(
                self.__margin_box__,
                color=self.__debug_layout_bound_color__,
                line_width=self.__debug_line__
            )

    def __draw_child__(self) -> None:
        """绘制子级"""
        with gpu.matrix.push_pop():
            last_offset = Vector((0, 0))
            for child in self.__children__:
                gpu.matrix.translate(last_offset)
                child.__layout__()
                last_offset = child.child_offset(self)

    def __draw_haver__(self) -> None:
        """绘制haver"""
        if self.is_draw_haver:
            # 操作符处理
            pm = self.parent.__menu_haver__
            if self.type.is_menu and self.level not in pm:
                hv = pm.values()
                if self.__menu_id__ not in hv:
                    self.parent.__menu_haver__[self.level] = self.__menu_id__

            self.___draw_background_color___(self.__background_haver_color__)

    def __draw_active__(self) -> None:
        """绘制active"""
        if self.active:
            self.___draw_background_color___(self.__background_active_color__)

    def __draw_alert__(self) -> None:
        if self.alert:
            self.___draw_background_color___(self.__background_alert_color__)

    def ___draw_background_color___(self, color: list):
        if self.parent.type.is_horizontal_layout:
            w, h = self.__draw_width__, self.parent.__child_max_height__
        else:
            w, h = self.parent.__child_max_width__, self.__draw_height__
        with gpu.matrix.push_pop():
            gpu.matrix.translate((w / 2, h / 2))
            self.draw_rounded_rectangle_area([0, 0], radius=5,
                                             color=color,
                                             width=w,
                                             height=h, segments=24)

    def __draw_menu__(self) -> None:
        """
        如果超过当前区域就画在左边,如果没有就画在右边
        如果两边都超了
        """
        self.__draw_item__()
        if self.__menu_id__ in self.parent_top.__menu_haver__.values():
            with (((gpu.matrix.push_pop()))):
                if IS_DEBUG_POINT:
                    self.draw_2d_points(Vector((0, 0)), color=(1, 0.5, 0.5, 1), point_size=10)

                gpu.matrix.translate(self.___menu_child_offset_position___)

                if IS_DEBUG_POINT:
                    self.draw_2d_points(Vector((0, 0)), color=(1, 0.5, 0, 1), point_size=10)

                with gpu.matrix.push_pop():
                    w = self.__child_max_width__ + self.layout_margin * 2
                    h = self.__child_sum_height__ + self.layout_margin * 2

                    gpu.matrix.translate((w / 2, h / 2))
                    self.__draw_layout__()
                    self.draw_rounded_rectangle_area(
                        [0, 0],
                        radius=self.__layout_radius__,
                        color=self.__background_normal_color__,
                        width=w,
                        height=h,
                        segments=self.__layout_segments__)

                if IS_DEBUG_DRAW:
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate(self.__layout_margin_vector__)
                        self.draw_2d_line(
                            __box_path__(self.__child_max_width__, self.__child_sum_height__),
                            color=self.__debug_menu_margin_color__,
                            line_width=self.__debug_line__)
                    self.draw_2d_line(
                        __box_path__(self.__child_max_width__ + self.layout_margin * 2,
                                     self.__child_sum_height__ + self.layout_margin * 2),
                        color=self.__debug_menu_bound_color__,
                        line_width=self.__debug_line__
                    )
                if IS_DEBUG_POINT:
                    self.draw_2d_points(Vector((0, 0)), color=(0, 0, 1, 1), point_size=10)

                with gpu.matrix.push_pop():
                    gpu.matrix.translate(self.__child_margin_vector__)
                    self.__draw_child__()
                self.__draw_menu_child_layout_position_debug__()

    @property
    def __margin_box__(self):
        """边距框"""
        height = self.__draw_height__
        width = self.__draw_width__
        return __box_path__(width, height)

    @property
    def __bound_box__(self):
        """边界框"""
        if self.type.is_horizontal_layout:
            return __box_path__(self.__child_sum_width__, self.__child_max_height__)
        elif self.type.is_vertical_layout or self.type.is_parent:
            return __box_path__(self.__child_max_width__, self.__child_sum_height__)
        return __box_path__(self.__text_width__, self.__text_height__)

    def check_haver(self):
        """检查haver"""
        pt = self.parent_top
        if self.type.is_menu and self.__child_menu_is_haver__:
            pt.__layout_haver__.append(self)
        if self.is_haver:
            pt.__layout_haver__.append(self)

        if self.parent:
            for child in self.__children__:
                if child.is_haver:
                    if child.level in self.__menu_haver__:
                        if self.type.is_menu:
                            mi = getattr(child, "__menu_id__", False)
                            if mi and mi != pt.__menu_haver__[child.level]:
                                pt.__menu_haver__[child.level] = mi
        if self.type.is_draw_text and self.is_haver:
            keys = list(pt.__menu_haver__.keys())
            for k in keys:
                if k >= self.level:
                    pt.__menu_haver__.pop(k)
