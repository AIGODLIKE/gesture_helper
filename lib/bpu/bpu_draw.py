import blf
import bpy
import gpu
from mathutils import Vector

from .bpu_debug import BpuDebug
from .bpu_measure import BpuMeasure
from ...utils.public_gpu import PublicGpu


def __box_path__(width: int, height: int) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
    return [0, 0], [0, height], [width, height], [width, 0], [0, 0]


IS_DEBUG_DRAW: bool = True
IS_DEBUG_INFO: bool = True


class BpuDraw(BpuMeasure, PublicGpu, BpuDebug):
    def __init__(self):
        super().__init__()

    def __gpu_draw__(self):
        """gpu绘制主方法"""
        if IS_DEBUG_DRAW:
            print("\n")

        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        area = bpy.context.region

        self.__measure__()
        self.__layout_haver_list__ = []
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.offset_position)

            self.draw_2d_points(Vector([0, 0]), color=(1, 0, 0, 0.3), point_size=50)

            with gpu.matrix.push_pop():
                gpu.matrix.translate((-500, 100))
                for index, i in enumerate((
                        str(bpy.context.area.type),
                        str(self.offset_position),
                        str(self.mouse_position),
                        str(self.__active_operator__),
                        f"haver:{self.__menu_haver_map__}",
                        f"{self.__layout_haver_list__}",)
                ):
                    self.draw_text([0, 50 + -50 * index], text=i, font_id=self.font_id)

            self.__layout__()

    def __layout__(self) -> None:
        """
        先测量宽高
        然后绘制子级
        """
        if self.type.is_parent:
            self.__draw_layout__()
            # print(f"draw parent layout \n{self.__draw_size__}\n{self.__child_max_width__}\n{self.type, self.__child_width_list__}")
        elif self.type.is_separator:
            self.__draw_separator__()
        elif self.type.is_menu:
            self.__draw_menu__()
        elif self.type.is_layout:
            self.__draw_layout__()
        elif self.type.is_draw_item:
            self.__draw_item__()

        self.__draw_debug__()
        if self.is_draw_child:
            self.__draw_child__()
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

            # print(f"separator:{parent.__child_max_height__,parent.__child_max_width__}\n{vs}\n")
            self.draw_2d_line(vs, color=[.4, .4, .4, 1], line_width=2)

    def __draw_item__(self) -> None:
        """绘制项"""
        if IS_DEBUG_DRAW:
            self.draw_2d_line(self.__margin_box__, color=(0, 0.6, 0, .8),  # 绿
                              line_width=1)

        self.__draw_haver__()
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.__margin_vector__)
            if IS_DEBUG_DRAW:
                self.draw_2d_line(self.__bound_box__, color=(0.6, 0, 0, .8),  # 红
                                  line_width=1)
            font_id = self.font_id
            blf.position(font_id, 0, 0, self.level)
            blf.color(font_id, *(1, 1, 1, 1))
            blf.size(font_id, self.font_size)
            blf.draw(font_id, self.__text__)

    def __draw_layout__(self) -> None:
        """绘制layout"""
        with gpu.matrix.push_pop():
            gpu.matrix.translate((self.__draw_width__ / 2, self.__draw_height__ / 2))
            self.draw_rounded_rectangle_area([0, 0], radius=10, color=[.01, .01, .01, 1], width=self.__draw_width__,
                                             height=self.__draw_height__, segments=40)
        if IS_DEBUG_DRAW:
            self.draw_2d_line(self.__margin_box__, color=[0.590620, 0.012983, 0.013702, 1.000000],  # 红
                              line_width=1)

            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.parent_offset())
                self.draw_2d_line(self.__bound_box__, color=[0.052861, 0.205076, 1.000024, 1.000000],  # 绿
                                  line_width=1)

    def __draw_child__(self) -> None:
        """绘制子级"""
        with gpu.matrix.push_pop():
            po = self.parent_offset()
            gpu.matrix.translate(po)

            last_offset = Vector([0, 0])
            offset_vector = po
            for child in self.draw_children:
                gpu.matrix.translate(last_offset)
                offset_vector += last_offset
                last_offset = child.child_offset(self)

                child.__item_position__ = offset_vector
                child.__layout__()

    def __draw_haver__(self) -> None:
        """绘制haver"""
        if self.is_draw_haver:
            # 操作符处理
            if self.type.is_operator:
                self.parent_top.__active_operator__ = self
                self.parent_top.__mouse_in_area__ = True
            elif self.parent_top.__active_operator__:
                self.parent_top.__active_operator__ = None

            if self.type.is_menu:
                self.__menu_haver_map__[self.__menu_id__] = self

            if self.parent.type.is_horizontal_layout:
                w, h = self.__draw_width__, self.parent.__child_max_height__
            else:
                w, h = self.parent.__child_max_width__, self.__draw_height__
            with gpu.matrix.push_pop():
                gpu.matrix.translate((w / 2, h / 2))
                self.draw_rounded_rectangle_area([0, 0], radius=5, color=[0.52861, 0.52861, 0.52861, 1.000000], width=w,
                                                 height=h, segments=24)

    def __draw_menu__(self) -> None:
        """
        如果超过当前区域就画在左边,如果没有就画在右边
        如果两边都超了
        """
        self.__draw_item__()
        if self.__menu_id__ in self.parent_top.__menu_haver_map__:
            with gpu.matrix.push_pop():
                tv = Vector((self.parent.__child_max_width__ + self.__margin__, 0)) - Vector(
                    (0, self.__child_draw_height__ - self.__draw_height__))
                gpu.matrix.translate(tv)

                self.__child_menu_offset_position__ += self.__item_position__ + tv + self.__margin_vector__
                for child in self.draw_children:
                    child.__child_menu_offset_position__ += self.__child_menu_offset_position__
                with gpu.matrix.push_pop():
                    w = self.__child_max_width__ + self.__mt__
                    h = self.__child_sum_height__ + self.__mt__

                    gpu.matrix.translate((w / 2, h / 2))

                    self.draw_rounded_rectangle_area([0, 0], radius=10, color=[.01, .01, .01, 1], width=w, height=h,
                                                     segments=40)

                self.__draw_child__()

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
        if self.is_draw_child:
            if self.is_haver:
                self.parent_top.__layout_haver_list__.append(self)
        # if getattr(self, "__menu_id__", False) and self.__menu_id__ in self.parent_top.__menu_haver_map__:
        #     # if not self.__child_menu_haver__:
        #     # self.parent_top.__menu_haver_map__.pop(self.__menu_id__)
        #     print(f"__child_haver__\t{self.__child_menu_haver__}")
        # ih = self.is_haver
        # la = self.level
        # if not ih:
        #     # 没在里面
        #     self.__menu_haver_map__.clear()
        # elif la in self.__menu_haver_map__:
        #     self.__menu_haver_map__.pop(la)
