import blf
from mathutils import Vector

from .bpu_property import BpuProperty


class BpuMeasure(BpuProperty):
    # text  不含边距
    __text_width__ = -1
    __text_height__ = -1

    # layout  不含边距
    __child_height_list__ = []
    __child_width_list__ = []

    __is_measurements_completed__ = False  # 是已完成测量
    separator_size = 5

    def __init__(self):
        super().__init__()
        self.__is_measurements_completed__ = False
        self.__child_height_list__ = []
        self.__child_width_list__ = []

    @property
    def __child_max_width__(self) -> int:
        if self.__child_width_list__:
            return max(self.__child_width_list__)
        return -10

    @property
    def __child_max_height__(self) -> int:
        if self.__child_height_list__:
            return max(self.__child_height_list__)
        return -10

    def __measure__(self) -> None:
        """测量数据"""
        if self.__is_measurements_completed__:
            # 测量过,跳过
            return

        self.__child_height_list__ = []
        self.__child_width_list__ = []
        # 如果是分割线就不测量,使用父级的宽高
        if self.type.is_menu:
            self.__measure_text__()
            self.__measure_children__()
        if self.type.is_draw_text:
            self.__measure_text__()
        if self.type.is_draw_child:
            self.__measure_children__()

        self.__is_measurements_completed__ = True

    def __measure_text__(self) -> None:
        """测量文字"""
        blf.size(self.font_id, self.font_size)
        (self.__text_width__, self.__text_height__) = blf.dimensions(self.font_id, self.__text__)

    def __measure_children__(self) -> None:
        """测量子级"""
        for child in self.__draw_children__:
            child.__measure__()
            self.__child_width_list__.append(child.__draw_width__)
            self.__child_height_list__.append(child.__draw_height__)
        self.__child_sum_width__ = sum(self.__child_width_list__)
        self.__child_sum_height__ = sum(self.__child_height_list__)

    @property
    def __draw_height__(self) -> int:
        """绘制高度
        只有在绘制layout的时侯才需要此属性"""
        self.__measure__()

        mt = self.__mt__
        if self.type.is_menu:
            return self.__text_height__ + mt
        elif self.type.is_separator:
            return self.separator_size + mt
        elif self.type.is_horizontal_layout:
            return self.__child_max_height__ + mt
        elif self.type.is_vertical_layout or self.type.is_parent:
            return self.__child_sum_height__ + mt

        # 文字
        return self.__text_height__ + mt

    @property
    def __draw_width__(self) -> int:
        """绘制宽度
        只有在绘制layout的时侯才需要此属性"""
        self.__measure__()

        mt = self.__mt__

        if self.type.is_menu:
            return self.__text_width__ + mt
        elif self.type.is_separator:
            parent_type = self.parent.type
            if parent_type.is_vertical_layout:
                return self.parent.__child_max_width__
            elif parent_type.is_horizontal_layout:
                return self.parent.__child_max_height__
        elif self.type.is_horizontal_layout:
            return self.__child_sum_width__ + mt
        elif self.type.is_vertical_layout or self.type.is_parent:
            return self.__child_max_width__ + mt

        # 文字
        return self.__text_width__ + mt

    @property
    def __draw_size__(self) -> Vector:
        """绘制大小"""
        return Vector([self.__draw_width__, self.__draw_height__])

    def child_offset(self, parent: 'BpuMeasure') -> Vector:
        """
        子级偏移量
        :param parent:
        :return:
        """
        if parent.type.is_parent:
            return Vector((0, self.__draw_height__))
        elif parent.type.is_horizontal_layout:
            return Vector((self.__draw_width__, 0))
        elif parent.type.is_vertical_layout or parent.type.is_menu:
            return Vector((0, self.__draw_height__))
        else:
            return self.__draw_size__

    def parent_offset(self) -> Vector:
        """父级偏移"""
        margin = self.__margin__
        if self.type.is_parent:
            return Vector([margin, margin])
        else:
            return Vector([margin, margin])

    @property
    def is_haver(self) -> bool:
        """是活动项"""
        start_x, start_y = start = self.offset_position + self.item_position
        if self.parent is not None:
            if self.parent.type.is_vertical_layout:
                end_x, end_y = start_x + self.parent.__child_max_width__, start_y + self.__draw_height__
            elif self.parent.type.is_horizontal_layout:
                end_x, end_y = start_x + self.__draw_width__, start_y + self.parent.__child_max_height__
            else:
                end_x, end_y = start + self.__draw_size__
        else:
            end_x, end_y = start + self.__draw_size__

        x, y = self.mouse_position
        in_x = start_x < x < end_x
        in_y = start_y < y < end_y
        return in_x and in_y

    @property
    def is_draw_haver(self) -> bool:
        """是可以绘制haver的
        只绘制操作符或者子菜单
        """
        return self.is_haver and (self.type.is_clickable or self.type.is_menu)
