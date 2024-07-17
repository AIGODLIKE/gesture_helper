import bpy
import gpu
from mathutils import Vector

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

        # self.draw_tips()
        print("draw_layout", flush=True)
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.mouse_position)

            self.draw_2d_points(Vector([0, 0]), color=(1, 0, 0, 1))
            self.draw_text([-200, 0], text=str(bpy.context.area.type), size=24)
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__margins_vector__)
                self.draw_layout()
            print("\n\n")

    def draw_tips(self):
        self.draw_rectangle(0, 0, 300, 100, color=[0.800424, 0.085840, 0.174684, 1.000000])
        self.draw_text([0, 0], text="编辑手势中 按右键退出", column=-2, color=(1, 1, 1, 1), size=24)

    def draw_layout(self):
        """
        先测量宽高
        然后绘制子级

        :return:
        """

        print("  " * self.level, self.type, f"\tmeasure:{self.__measure__[0], self.__measure__[1]}",
              f"\ttext:{self.text}",
              f"\tmargins_vector:{self.__margins_vector__[0], self.__margins_vector__[1]}", flush=True)
        if self.type.is_layout:
            measure = self.__measure__
            self.draw_rectangle(0, 0, measure[0], measure[1])
        elif self.type.is_draw_item:
            self.draw_text([0, 0], text=self.text)

        if self.is_draw_child:
            self.draw_children_layout()

    def draw_children_layout(self):
        # print("  draw_children_layout", hash(self), self.type, self.__draw_children__, flush=True)
        for child in self.draw_children:
            gpu.matrix.translate(child.__measure_vector__(self))  # 内容偏移
            # gpu.matrix.translate(child.__margins_vector__)  # 间隔偏移
            child.draw_layout()
