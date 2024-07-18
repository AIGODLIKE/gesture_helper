import blf
from mathutils import Vector

from .bpu_property import BpuProperty


class BpuMeasure(BpuProperty):
    @property
    def margin(self) -> int:
        """边距"""
        if self.is_layout:
            return 0
        return 5

    # text  不含边距
    __width__ = -1
    __height__ = -1

    # layout  不含边距
    __height_list__ = []
    __width_list__ = []

    __is_measurements_completed__ = False  # 是已完成测量

    def __init__(self):
        super().__init__()
        self.__is_measurements_completed__ = False
        self.__height_list__ = []
        self.__width_list__ = []

    @property
    def __max_width__(self):
        if self.__width_list__:
            return max(self.__width_list__)
        return -1

    @property
    def __max_height__(self):
        if self.__height_list__:
            return max(self.__height_list__)
        return -1

    def __measure__(self):
        """测量数据"""
        if self.__is_measurements_completed__:
            # 测量过,跳过
            return

        self.__height_list__ = []
        self.__width_list__ = []

        if self.type.is_draw_text:
            from .bpu_draw import FONT_SIZE
            blf.size(self.font_id, FONT_SIZE)
            (self.__width__, self.__height__) = blf.dimensions(self.font_id, self.text)
        elif self.type.is_layout:
            for child in self.__draw_children__:
                child.__measure__()
                self.__width_list__.append(child.__width__)
                self.__height_list__.append(child.__height__)
            self.__width__ = sum(self.__width_list__)  # + self.margin
            self.__height__ = sum(self.__height_list__)  # + self.margin
            print("\tis_layout child", f"sm:{sum(self.__height_list__)}",
                  f"hl:{self.__height_list__} h:{self.__height__}", f"m:{self.margin}")
        self.__is_measurements_completed__ = True

    @property
    def draw_height(self):
        """绘制高度
        只有在绘制layout的时侯才需要此属性"""
        self.__measure__()
        if self.type.is_horizontal_layout:
            return self.__max_height__  # + self.margin * 2
        elif self.type.is_vertical_layout:
            return self.__height__  # + self.margin * 2

        # 文字
        return self.__height__  # + self.margin * 2

    @property
    def draw_width(self):
        """绘制宽度
        只有在绘制layout的时侯才需要此属性"""
        self.__measure__()

        if self.type.is_horizontal_layout:
            return self.__width__  # + self.margin * 2
        elif self.type.is_vertical_layout:
            return self.__max_width__  # + self.margin * 2

        # 文字
        return self.__width__  # + self.margin * 2

    @property
    def draw_size(self):
        return self.draw_width, self.draw_height

    def child_offset(self, parent: 'BpuMeasure') -> Vector:
        """
        子级偏移量
        :param parent:
        :return:
        """
        self.__measure__()
        if parent.type.is_parent:
            return Vector([0, 0])
        elif parent.type.is_horizontal_layout:
            return Vector((self.draw_width, 0))
        elif parent.type.is_vertical_layout:
            return Vector((0, self.draw_height))
        else:
            return Vector(self.draw_size)

    def margin_offset(self, parent: 'BpuMeasure') -> Vector:
        return Vector([0, 0])
        if (parent and parent.type.is_parent) or self.type.is_parent:
            return Vector([0, 0])
        elif parent.type.is_horizontal_layout:
            return Vector((self.margin, 0))
        elif parent.type.is_vertical_layout:
            return Vector((0, self.margin))
        else:
            return Vector([self.margin, self.margin])

    def parent_offset(self, parent: 'BpuMeasure' = None):
        return Vector([0, 0])
        if (parent and parent.type.is_parent) or self.type.is_parent:
            return Vector([0, 0])
        else:
            return Vector([self.margin, self.margin])
        # if self.type.is_horizontal_layout:
        #     return Vector((0, self.margin))
        # elif self.type.is_vertical_layout:
        #     return Vector((self.margin, 0))
        # else:
