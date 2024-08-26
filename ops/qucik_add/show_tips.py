import gpu.matrix

from ...src.lib.bpu import BpuLayout


class GestureShowTips(BpuLayout):

    def __init__(self):
        super().__init__()
        self.__background_normal_color__ = [.5, .1, .1, 0.7]
        self.font_size = 18

    def __gpu_draw__(self):
        self.__measure__()
        self.__layout_haver__ = list()
        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.offset_position)
            gpu.matrix.translate(self.__quadrant_translate__)
            self.__layout__()
        self.__layout_haver_histories__ = self.__layout_haver__
