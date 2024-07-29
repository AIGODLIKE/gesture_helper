import gpu.matrix
from mathutils import Vector

from .bpu_measure import BpuMeasure


class BpuPropLayout(BpuMeasure):

    def __draw_property__(self):
        if self.__property_type__ == "BOOLEAN":
            color = (.5, 0, 0, 1)
            h = self.__text_height__
            from .bpu_draw import __box_path__
            if self.__property_value__:
                with gpu.matrix.push_pop():
                    gpu.matrix.translate(self.__margin_vector__)
                    self.draw_2d_line(
                        __box_path__(h, h),
                        color=color,
                        line_width=self.__line__
                    )
                    from ...utils.texture import Texture
                    self.draw_image([0, 0], h, h, Texture.get("TICK"))
            else:
                with gpu.matrix.push_pop():
                    gpu.matrix.translate(self.__margin_vector__)
                    self.draw_2d_line(
                        __box_path__(h, h),
                        color=color,
                        line_width=self.__line__
                    )
            with gpu.matrix.push_pop():
                gpu.matrix.translate(Vector([self.__draw_height__, 0]))
                self.__draw_item__()
        self.__draw_haver_position_debug__()
