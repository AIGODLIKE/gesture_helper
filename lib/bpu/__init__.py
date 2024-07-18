from mathutils import Vector

from .bpu_draw import BpuDraw
from .bpu_event import BpuEvent
from .bpu_property import BpuProperty
from .bpu_register import BpuRegister
from .bpu_type import BPUType


class BpuLayout(BpuDraw, BpuRegister, BpuEvent):

    def __init__(self):
        super().__init__()
        self.type = BPUType.PARENT

    def __repr__(self):
        return f"BpuLayout{self.type, self.text, id(self)}"  # self.__measure__

    def __layout__(self, layout_type: BPUType) -> "BpuLayout":
        """布局
        绘制及测量时根据布局类型 计算方法"""
        layout = BpuLayout()
        layout.type = layout_type
        layout.font_id = self.font_id
        layout.level = self.level + 1
        layout.font_size = self.font_size
        layout.layout_margin = self.layout_margin
        layout.text_margin = self.text_margin
        layout.parent = self

        layout.item_position = Vector([0, 0])
        layout.offset_position = self.offset_position
        layout.mouse_position = self.mouse_position

        if self.type == BPUType.PARENT:
            self.__temp_children__.append(layout)
        else:
            self.__draw_children__.append(layout)
        layout.__clear_children__()
        return layout

    def label(self, text="Hollow Word"):
        lab = self.__layout__(BPUType.LABEL)
        lab.text = text

    def box(self) -> "BpuLayout":
        return self.__layout__(BPUType.BOX)

    def row(self) -> "BpuLayout":
        return self.__layout__(BPUType.ROW)

    def column(self) -> "BpuLayout":
        return self.__layout__(BPUType.COLUMN)

    def split(self, factor=0.0, align=False) -> "BpuLayout":
        return self.__layout__(BPUType.SPLIT)

    def operator(self, operator, text=""):
        return self.__layout__(BPUType.OPERATOR)

    # def __tree__(self):
    #     ...

    def __enter__(self):
        self.__clear_children__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.type == BPUType.PARENT:
            self.__draw_children__ = self.__temp_children__
