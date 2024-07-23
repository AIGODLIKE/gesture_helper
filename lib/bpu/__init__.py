import bpy
from mathutils import Vector

from .bpu_draw import BpuDraw
from .bpu_event import BpuEvent
from .bpu_operator import BpuOperator, OperatorProperties
from .bpu_property import BpuProperty
from .bpu_register import BpuRegister
from .bpu_type import BPUType


class BpuLayout(BpuDraw, BpuOperator, BpuRegister, BpuEvent):

    def __init__(self):
        super().__init__()
        self.type = BPUType.PARENT

    def __repr__(self):
        return f"BpuLayout{self.type, self.__text__}"  # self.__measure__

    def __child_layout__(self, layout_type: BPUType) -> "BpuLayout":
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

        layout.__item_position__ = Vector([0, 0])
        layout.__child_menu_offset_position__ = Vector([0, 0])
        layout.offset_position = self.offset_position
        layout.mouse_position = self.mouse_position
        if self.type == BPUType.PARENT:
            self.__temp_children__.append(layout)
        else:
            self.__draw_children__.append(layout)
        layout.__clear_children__()
        return layout

    def label(self, text="Hollow Word"):
        """标签"""
        lab = self.__child_layout__(BPUType.LABEL)
        lab.text = text

    def row(self) -> "BpuLayout":
        """行"""
        return self.__child_layout__(BPUType.ROW)

    def column(self) -> "BpuLayout":
        """列"""
        return self.__child_layout__(BPUType.COLUMN)

    def separator(self, show_line=True) -> None:
        """分割"""
        sep = self.__child_layout__(BPUType.SEPARATOR)
        sep.__show_separator_line__ = show_line

    def menu(self, text, menu_id="menu") -> "BpuLayout":
        """菜单"""
        if text is None:
            import traceback
            traceback.print_exc()
            traceback.print_stack()
            Exception("Menu Error not text")
        m = self.__child_layout__(BPUType.MENU)
        m.text = text
        m.__menu_id__ = menu_id
        return m

    def operator(self, operator: str, text=None) -> "bpy.types.OperatorProperties":
        if operator is None:
            Exception("Error not operator")
        ops = self.__child_layout__(BPUType.OPERATOR)
        ops.__bl_idname__ = operator
        ops.text = text
        ops.__operator_properties__ = OperatorProperties()
        return ops.__operator_properties__

    # def split(self, factor=0.0, align=False) -> "BpuLayout":
    #     return self.__child_layout__(BPUType.SPLIT)

    def __enter__(self):
        self.__clear_children__()
        self.__mouse_in_area__ = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.type == BPUType.PARENT:
            if not self.__mouse_in_area__:
                self.__active_operator__ = None
            self.__draw_children__ = self.__temp_children__
