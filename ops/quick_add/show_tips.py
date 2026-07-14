import gpu.matrix

from ...src.lib.bpu import BpuLayout
from ...utils.public_gpu import gpu_draw_begin, gpu_draw_end


class GestureShowTips(BpuLayout):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__background_normal_color__ = [0.12, 0.04, 0.04, 0.85]
        self.__outline_color__ = [0.55, 0.25, 0.25, 1.0]
        self.font_size = 18

    def __gpu_draw__(self):
        self.__measure__()
        self.__layout_haver__ = list()
        gpu_draw_begin()
        try:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.offset_position)
                gpu.matrix.translate(self.__quadrant_translate__)
                self.__layout__()
        finally:
            gpu_draw_end()
        self.__layout_haver_histories__ = self.__layout_haver__
