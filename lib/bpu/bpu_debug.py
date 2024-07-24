import blf
import gpu
from mathutils import Vector


class BpuDebug:

    @property
    def __is_debug__(self):
        return False
        return self.parent and self.parent.type.is_menu and self.type.is_menu

    def __draw_debug__(self) -> None:
        """绘制debug层"""
        from .bpu_draw import IS_DEBUG_INFO
        if IS_DEBUG_INFO and self.__is_debug__:
            size = 24
            offset = Vector((-500, -200))
            for index, i in enumerate(
                    (
                            f"parent:{self.parent}",
                            str(self.is_haver),
                            str(self.__draw_size__),
                            str(self.offset_position),
                            str(self.mouse_position),
                    )[::-1]
            ):
                font_id = self.font_id
                blf.size(font_id, size)
                w, h = blf.dimensions(font_id, i)
                offset += Vector((0, h))
                blf.color(font_id, 1, 0, 0, 1)
                blf.position(font_id, offset[0], offset[1], 99)
                blf.draw(font_id, i)
                offset += Vector((0, 20,))

    def __draw_haver_position_debug__(self):
        op = self.offset_position
        a = self.mouse_position - op
        # text = f"{op.x:.0f} {op.y:.0f}  {a.x:.0f} {a.y:.0f}"
        text = f"{'H' if self.is_haver else ''}"
        w = self.parent.__child_max_width__ if (self.parent is not None) else self.__draw_width__
        self.___draw_haver_debug___(Vector((w, self.__draw_height__)), text)

    def __draw_menu_child_layout_position_debug__(self):
        op = self.offset_position + self.__menu_child_offset_position__
        a = self.mouse_position - op
        # text = f"{op.x:.0f} {op.y:.0f}\t{a.x:.0f} {a.y:.0f}"
        text = f"{'MH' if self.__child_menu_is_haver__ else ''}"
        v = Vector((self.__child_max_width__, self.__child_sum_height__)) + self.__layout_margin_vector__ * 2
        self.___draw_haver_debug___(v, text)

    def ___draw_haver_debug___(self, point_b: Vector, string: str):
        from .bpu_draw import IS_DEBUG_POINT, IS_DEBUG_HAVER

        if IS_DEBUG_POINT:
            self.draw_2d_points(Vector((0, 0)), color=(0.5, 0, 0, 1), point_size=10)
        if IS_DEBUG_HAVER:
            font_id = self.font_id
            blf.position(font_id, 0, 0, self.level)
            blf.color(font_id, *[1.000000, 0.525200, 0.023322, 1.000000])
            blf.size(font_id, 20)
            blf.draw(font_id, string)
        if IS_DEBUG_POINT:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(point_b)
                self.draw_2d_points(Vector((0, 0)), color=(0.5, 0.5, 0, 1), point_size=10)
