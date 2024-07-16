import bpy
import gpu
from gpu_extras.presets import draw_circle_2d

from .bpu_property import BpuProperty
from ...utils.public_gpu import PublicGpu


class BpuDraw(BpuProperty, PublicGpu):
    def __init__(self):
        super().__init__()

    def gpu_draw(self):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        area = bpy.context.region
        self.draw_tips()
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.mouse_position)

            draw_circle_2d([0, 0], [1, 0.5, 0.5, 0], 100.0)
            self.draw_text([0, 0], size=64)
            self.draw_text([0, 0], text=str(bpy.context.area.type), size=24)

            self.draw_layout()

    def draw_tips(self):
        self.draw_rectangle(0, 0, 300, 100, color=[0.800424, 0.085840, 0.174684, 1.000000])
        self.draw_text([0, 0], text="编辑手势中 按右键退出", column=-2, color=(1, 1, 1, 1), size=24)

    def draw_layout(self):
        """
        先测量宽高
        然后绘制子级

        :return:
        """
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.__margins_vector__)
            if self.type.is_layout:
                measure = self.__measure__
                self.draw_rectangle(0, 0, measure[0], measure[1])
            elif self.type.is_draw_item:
                ...
                self.draw_text([0, 0], text=self.text)

            self.draw_children_layout()

    def draw_children_layout(self):
        for child in self.children:
            with gpu.matrix.push_pop():
                child.draw_layout()
