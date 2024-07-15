from .bpu_draw import BpuDraw
from .bpu_event import BpuEvent
from .bpu_property import BpuProperty
from .bpu_register import BpuRegister
from .bpu_type import BPUType


class BpuLayout(BpuDraw, BpuRegister, BpuEvent):

    @property
    def preset(self) -> "BpuLayout":
        ...

    @property
    def children(self) -> dict["BpuLayout"]:
        ...

    def __measure__(self):
        """测量数据"""
        ...

    def box(self) -> "BpuLayout":
        ...

    def row(self) -> "BpuLayout":
        ...

    def column(self) -> "BpuLayout":
        ...

    def split(self, factor=0.0, align=False) -> "BpuLayout":
        ...

    def operator(self, operator, text=""):
        ...
