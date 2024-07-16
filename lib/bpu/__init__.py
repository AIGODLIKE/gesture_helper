from .bpu_draw import BpuDraw
from .bpu_event import BpuEvent
from .bpu_property import BpuProperty
from .bpu_register import BpuRegister
from .bpu_type import BPUType


class BpuLayout(BpuDraw, BpuRegister, BpuEvent):

    def __init__(self):
        super().__init__()
        self.type = BPUType.PARENT

    def __layout__(self, layout_type: BPUType) -> "BpuLayout":
        """布局
        绘制及测量时根据布局类型 计算方法"""
        layout = BpuLayout()
        layout.type = layout_type
        layout.font_id = self.font_id
        if self.type == BPUType.PARENT:
            self._temp_children.append(layout)
        else:
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

    def __tree__(self):
        ...

    def __enter__(self):
        self.is_updating = True
        self._temp_children = []
        self.children = []
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.is_updating = False
        self.children = self._temp_children
