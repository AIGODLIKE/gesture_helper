import blf
import bpy
import gpu
from mathutils import Vector

from .bpu_measure import BpuMeasure
from ...utils.public_gpu import PublicGpu


def __box_path__(width: int, height: int) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
    return [0, 0], [0, height], [width, height], [width, 0], [0, 0]


IS_DEBUG_DRAW: bool = True
IS_DEBUG_XY: bool = True


class BpuDraw(BpuMeasure, PublicGpu):
    def __init__(self):
        super().__init__()

    def __gpu_draw__(self):
        """gpu绘制主方法"""
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        area = bpy.context.region

        self.__measure__()
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.offset_position)

            self.draw_2d_points(Vector([0, 0]), color=(1, 0, 0, 0.3), point_size=50)

            with gpu.matrix.push_pop():
                gpu.matrix.translate((-500, 100))
                self.draw_text([0, 50], text=str(bpy.context.area.type), font_id=self.font_id)
                self.draw_text([0, 0], text=str(self.offset_position), font_id=self.font_id)
                self.draw_text([0, -50], text=str(self.mouse_position), font_id=self.font_id)
            self.__layout__()

    def __layout__(self) -> None:
        """
        先测量宽高
        然后绘制子级
        """
        if self.type.is_separator:
            self.__draw_separator__()
        elif self.type.is_layout:
            self.__draw_layout__()
        elif self.type.is_draw_item:
            self.__draw_item__()

        self.__draw_debug__()
        self.__draw_child__()

    def __draw_debug__(self) -> None:
        """绘制debug层"""
        if IS_DEBUG_XY:
            size = 15
            a = self.offset_position + self.item_position
            self.draw_text([0, 0], str(self.item_position), size=size, color=(1, 1, 1, 1))
            self.draw_text([300, 0], str(self.is_haver), size=size, color=(1, 0, 0, 1))
            self.draw_text([600, 0], str(a), size=size, color=(1, 0, 0, 1))
            self.draw_text([900, 0], str(a + self.draw_size), size=size, color=(1, 0, 0, 1))
            self.draw_text([1200, 0], f"parent:{self.parent}", size=size, color=(1, 0, 0, 1))

    def __draw_separator__(self):
        parent = self.parent
        if parent:
            pt = parent.type
            if pt.is_horizontal_layout:
                vs = [Vector((0, 0)), Vector((0, parent.__child_max_height__))]
            elif pt.is_vertical_layout:
                vs = [Vector((0, 0)), Vector((parent.__child_max_width__, 0))]
            else:
                vs = [Vector((0, 0)), Vector((5, 5))]
            with gpu.matrix.push_pop():
                if pt.is_horizontal_layout:
                    gpu.matrix.translate((self.draw_width / 2, 0))
                elif pt.is_vertical_layout:
                    gpu.matrix.translate((0, self.draw_height / 2))
                self.draw_2d_line(vs,
                                  color=[.28426, .28426, .28426, 1.000000],
                                  line_width=5)

    def __draw_item__(self) -> None:
        """绘制项"""
        if IS_DEBUG_DRAW:
            self.draw_2d_line(self.__margin_box__,
                              color=(0, 0.6, 0, .8),  # 绿
                              line_width=1)
        self.__draw_haver__()
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.__margin_vector__)
            if IS_DEBUG_DRAW:
                self.draw_2d_line(self.__bound_box__,
                                  color=(0.6, 0, 0, .8),  # 红
                                  line_width=1)
            font_id = self.font_id
            blf.position(font_id, 0, 0, self.level)
            blf.color(font_id, *(1, 1, 1, 1))
            blf.size(font_id, self.font_size)
            blf.draw(font_id, self.text)

    def __draw_layout__(self) -> None:
        """绘制layout"""
        with gpu.matrix.push_pop():
            gpu.matrix.translate((self.draw_width / 2, self.draw_height / 2))
            self.draw_rounded_rectangle_area([0, 0], radius=50, color=(0, 0, 0, 1.0), width=self.draw_width,
                                             height=self.draw_height, segments=15)
        if IS_DEBUG_DRAW:
            self.draw_2d_line(self.__margin_box__,
                              color=[0.590620, 0.012983, 0.013702, 1.000000],  # 红
                              line_width=1)

            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.parent_offset())
                self.draw_2d_line(self.__bound_box__,
                                  color=[0.052861, 0.205076, 1.000024, 1.000000],  # 绿
                                  line_width=1)

    def __draw_child__(self) -> None:
        """绘制子级"""
        if self.is_draw_child:
            with gpu.matrix.push_pop():
                po = self.parent_offset()
                gpu.matrix.translate(po)

                last_offset = Vector([0, 0])
                offset_vector = po
                for (index, child) in enumerate(self.draw_children):
                    gpu.matrix.translate(last_offset)
                    offset_vector += last_offset
                    last_offset = child.child_offset(self, index)

                    child.item_position = offset_vector
                    child.__layout__()

    def __draw_haver__(self) -> None:
        """绘制haver"""
        if self.is_draw_haver:
            if self.parent.type.is_horizontal_layout:
                w, h = self.draw_width, self.parent.__child_max_height__
            else:
                w, h = self.parent.__child_max_width__, self.draw_height
            with gpu.matrix.push_pop():
                gpu.matrix.translate((w / 2, h / 2))
                self.draw_rounded_rectangle_area([0, 0], radius=5, color=[0.52861, 0.52861, 0.52861, 1.000000],
                                                 width=w, height=h,
                                                 segments=15)

    @property
    def __margin_box__(self):
        """边距框"""
        height = self.draw_height
        width = self.draw_width
        return __box_path__(width, height)

    @property
    def __bound_box__(self):
        """边界框"""
        height = self.__height__
        width = self.__width__
        if self.type.is_horizontal_layout:
            return __box_path__(width, self.__child_max_height__)
        elif self.type.is_vertical_layout:
            return __box_path__(self.__child_max_width__, height)
        return __box_path__(width, height)
