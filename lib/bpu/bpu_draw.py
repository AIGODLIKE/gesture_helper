import blf
import bpy
import gpu
from mathutils import Vector

from .bpu_measure import BpuMeasure
from ...utils.public_gpu import PublicGpu


class BpuDraw(BpuMeasure, PublicGpu):
    def __init__(self):
        super().__init__()

    def gpu_draw(self):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        area = bpy.context.region

        # self.draw_tips()
        print("draw_layout", flush=True)
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.mouse_position)

            self.draw_2d_points(Vector([0, 0]), color=(1, 0, 0, 0.3), point_size=50)
            self.draw_text([-200, 50], text=str(bpy.context.area.type), font_id=self.font_id)
            self.draw_layout()
            print("\n\n")

    def draw_layout(self, parent: 'BpuMeasure' = None):
        """
        先测量宽高
        然后绘制子级

        :return:
        """

        print("  " * self.level, self.type, f"\tdraw_size:{self.draw_size}",
              f"\t\ttext:{self.text}", flush=True)

        if self.type.is_layout:
            self.draw_rectangle(0, 0, self.draw_width, self.draw_height)
        elif self.type.is_draw_item:
            self.draw_2d_line(self.__margin_box__,
                              color=(0, 0.6, 0, .8),  # 绿
                              line_width=1)

            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__margin_vector__)
                self.draw_2d_line(self.__bound_box__,
                                  color=(0.6, 0, 0, .8),  # 红
                                  line_width=1)
                font_id = self.font_id
                blf.position(font_id, 0, 0, self.level)
                blf.color(font_id, *(1, 1, 1, 1))
                blf.size(font_id, self.font_size)
                blf.draw(font_id, self.text)

        if self.is_draw_child:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.parent_offset(parent))
                last_offset = Vector([0, 0])
                for (index, child) in enumerate(self.draw_children):
                    gpu.matrix.translate(last_offset)
                    child.draw_layout(self)
                    last_offset = child.child_offset(self, index)

    @property
    def __margin_box__(self):
        height = self.draw_height
        width = self.draw_width
        return self.__box_path__(width, height)

    @property
    def __bound_box__(self):
        height = self.__height__
        width = self.__width__
        return self.__box_path__(width, height)

    def __box_path__(self, width, height):
        return [0, 0], [0, height], [width, height], [width, 0], [0, 0]
        # if self.type.is_layout:
        # else:
        #     return [0, 0], [0, -height], [width, -height], [width, 0], [0, 0]
