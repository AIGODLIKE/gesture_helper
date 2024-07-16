import blf
from mathutils import Vector

from .bpu_draw import BpuDraw
from .bpu_event import BpuEvent
from .bpu_property import BpuProperty
from .bpu_register import BpuRegister
from .bpu_type import BPUType


class BpuLayout(BpuDraw, BpuRegister, BpuEvent):
    children = []  # 子级,不需要父级

    def __init__(self):
        super().__init__()

    @property
    def __measure__(self) -> Vector:
        """测量数据"""
        if self._type.is_draw_text:
            blf.dimensions(text=self.text)
        elif self._type.is_layout:
            measure = Vector([0, 0])
            for child in self.children:
                measure += child.__measure__()
            return measure

    def __layout__(self, layout_type: BPUType) -> "BpuLayout":
        """布局
        绘制及测量时根据布局类型 计算方法"""
        layout = BpuLayout()
        layout._type = layout_type
        layout.font_id = self.font_id
        self.children.append(layout)
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
        ...

    def __enter__(self):
        print("Entering the context")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting the context")
