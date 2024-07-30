import gpu.matrix

from ...lib.bpu import BpuLayout


class GestureShowTips(BpuLayout):

    def __init__(self):
        super().__init__()
        self.__background_normal_color__ = [.8, .1, .1, 1]

    def __gpu_draw__(self):
        self.__measure__()
        self.__layout_haver__ = list()

        with gpu.matrix.push_pop():
            gpu.matrix.translate(self.offset_position)

            gpu.matrix.translate(self.__quadrant_translate__)
            self.__layout__()
        self.__layout_haver_histories__ = self.__layout_haver__
