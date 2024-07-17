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

            self.draw_2d_points(Vector([0, 0]), color=(1, 0, 0, 1), point_size=50)
            self.draw_text([-200, 50], text=str(bpy.context.area.type), size=24)
            self.draw_layout()
            print("\n\n")

    def draw_layout(self, parent: 'BpuMeasure' = None):
        """
        先测量宽高
        然后绘制子级

        :return:
        """
        blf.size(self.font_id, self.font_size)
        print("  " * self.level, self.type, f"\tdraw_size:{self.draw_size}", f"\ttext:{self.text}", flush=True)

        if self.type.is_layout:
            self.draw_rectangle(0, 0, self.draw_width, self.draw_height)
            self.draw_2d_line(([-10, 0], [-10, self.draw_height]), color=(0, 1, 0, 1))
        elif self.type.is_draw_item:
            # with gpu.matrix.push_pop():
            #     self.draw_rectangle(0, 0, self.draw_width, -self.draw_height - self.margin * 2, color=(0, 1, 0, 1))
            # with gpu.matrix.push_pop():
            self.draw_text([0, 0], text=self.text)

            self.draw_2d_line(([0, 0], [0, -self.draw_height]), color=(0, 1, 0, 1))

        if self.is_draw_child:
            with gpu.matrix.push_pop():
                po = self.parent_offset(parent)
                gpu.matrix.translate(po)
                # print("\t\tpo", po, self.type)
                for child in self.draw_children:
                    co = child.child_offset(self)
                    gpu.matrix.translate(co)

                    cm = child.margin_offset(self)
                    gpu.matrix.translate(cm)
                    # print(f"\t\t{child.type}\tchild translate", co)
                    child.draw_layout()
