import blf
from mathutils import Vector

from .bpu_property import BpuProperty


class BpuOffset:
    @property
    def ___menu_child_offset_position___(self) -> Vector:
        plm = self.parent.layout_margin
        a = Vector((self.parent.__child_max_width__ + plm, -(self.__child_sum_height__ + self.layout_margin * 2)))
        b = Vector((0, self.__draw_height__))
        if self.parent.type.is_menu:
            b -= Vector((0.5, 0))
        return a + b

    @property
    def __offset__(self):
        if self.type.is_parent:
            return self.offset_position

        if not self.parent:
            return Vector([-999, 0])

        p = self.parent
        index = p.__children__.index(self)
        cl = p.__children__[:index]
        w = Vector([sum([c.__draw_width__ for c in cl]), 0])
        h = Vector([0, sum([c.__draw_height__ for c in cl])])

        pt = p.type
        if pt.is_menu:
            m = p.__offset__ + p.___menu_child_offset_position___
            return m + self.__layout_margin_vector__ + h
        elif pt.is_parent:
            return h + p.__margin_vector__ + self.offset_position
        elif pt.is_horizontal_layout:
            return w + p.__margin_vector__ + p.__offset__
        elif pt.is_vertical_layout:
            return h + p.__margin_vector__ + p.__offset__
        else:
            return Vector([0, 0])


class BpuMeasure(BpuProperty, BpuOffset):
    # text  不含边距
    __text_width__: int
    __text_height__: int

    __child_height_list__: list
    __child_width_list__: list

    separator_size = 5

    def __init__(self):
        super().__init__()
        self.__clear_measure__()

    def __clear_measure__(self):
        self.__child_height_list__ = []
        self.__child_width_list__ = []
        self.__text_width__ = -100
        self.__text_height__ = -100

    # 子级总高宽
    @property
    def __child_sum_width__(self) -> int:
        return sum(self.__child_width_list__)

    @property
    def __child_sum_height__(self) -> int:
        return sum(self.__child_height_list__)

    @property
    def __child_max_width__(self) -> int:
        if self.__child_width_list__:
            return max(self.__child_width_list__)
        return -100

    @property
    def __child_max_height__(self) -> int:
        if self.__child_height_list__:
            return max(self.__child_height_list__)
        return -100

    def __measure__(self) -> None:
        """测量数据"""
        self.__clear_measure__()

        # 如果是分割线就不测量,使用父级的宽高
        if self.type.is_prop:
            self.__measure_prop__()
        if self.type.is_menu:
            self.__measure_text__()
            self.__measure_children__()
        if self.type.is_draw_text:
            self.__measure_text__()
        if self.type.is_draw_child:
            self.__measure_children__()

    def __measure_prop__(self) -> None:
        if self.__property_type__ == "BOOLEAN":
            if self.only_icon:  # 只显示图标,使用父级的宽高
                ...
            elif self.text:  # 使用自定义文字
                self.__measure_text__(self.text)
            elif self.__property_name_string__:  # 使用属性的值
                self.__measure_text__(str(self.__property_name_string__))

    def __measure_text__(self, text=None) -> None:
        """测量文字"""
        if not text:
            text = self.__text__
        blf.size(self.font_id, self.font_size)
        (self.__text_width__, self.__text_height__) = blf.dimensions(self.font_id, self.___translation_text___(text))

    def __measure_children__(self) -> None:
        """测量子级"""
        for child in self.__children__:
            child.__measure__()
            self.__child_height_list__.append(child.__draw_height__)
            self.__child_width_list__.append(child.__draw_width__)

    @property
    def ___draw_height_property___(self) -> int:
        pt = self.parent.type
        if self.__property_type__ == "BOOLEAN":
            if self.only_icon:
                if pt.is_horizontal_layout:
                    return self.parent.__child_max_height__
                elif pt.is_vertical_layout:
                    return self.parent.__child_max_width__
            elif self.text or self.__property_name_string__:
                # 使用文字
                return self.__text_height__

            if pt.is_horizontal_layout:
                return self.parent.__child_max_height__ + self.__text_width__
            elif pt.is_vertical_layout:
                return self.parent.__child_max_width__ + self.__text_width__
        return -1

    @property
    def ___draw_width_property___(self) -> int:
        pt = self.parent.type
        if self.__property_type__ == "BOOLEAN":
            if self.only_icon:
                if pt.is_horizontal_layout:
                    return self.parent.__child_max_height__
                elif pt.is_vertical_layout:
                    return self.parent.__child_max_height__
            elif self.text or self.__property_name_string__:
                # 使用文字 一个图标的高度+宽度
                return self.__text_width__ + self.__text_height__ + self.__mt__
            if pt.is_horizontal_layout:
                return self.parent.__child_max_height__ + self.__text_width__
            elif pt.is_vertical_layout:
                return self.parent.__child_max_height__ + self.__text_width__
        return -1

    @property
    def __draw_height__(self) -> int:
        """绘制高度
        只有在绘制layout的时侯才需要此属性"""
        mt = self.__mt__
        if self.type.is_menu:
            return self.__text_height__ + mt
        elif self.type.is_separator:
            return self.separator_size + mt
        elif self.type.is_horizontal_layout:
            return self.__child_max_height__ + mt
        elif self.type.is_vertical_layout or self.type.is_parent:
            return self.__child_sum_height__ + mt
        elif self.type.is_prop:
            h = self.___draw_height_property___ + mt
            return h
        # 文字
        return self.__text_height__ + mt

    @property
    def __draw_width__(self) -> int:
        """绘制宽度
        只有在绘制layout的时侯才需要此属性"""
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
        elif self.type.is_prop:
            w = self.___draw_width_property___ + mt
            # print(
            #     f"\t__draw_width__\t{w}\t{self.__property_rna__}\t{self.__property_value__}\t{self.__property_type__}\t{self.__text_width__}")
            return w
        # 文字
        return self.__text_width__ + mt

    @property
    def __draw_size__(self) -> Vector:
        """绘制大小"""
        return Vector((self.__draw_width__, self.__draw_height__))

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
        if (self.parent and self.parent.type.is_menu) or self.type.is_menu:
            p = self.parent.layout_margin
            return Vector((p, p))
        elif self.type.is_parent:
            return Vector((margin, margin))
        else:
            return Vector((margin, margin))

    @property
    def is_haver(self) -> bool:
        """是活动项"""
        offset = self.offset_position if self.type.is_parent else self.__offset__
        start_x, start_y = start = offset + self.parent_top.__quadrant_translate__
        if self.parent is not None:
            pt = self.parent.type
            if pt.is_horizontal_layout:  # 水平 row
                end_x, end_y = start_x + self.__draw_width__, start_y + self.parent.__child_max_height__
            elif pt.is_vertical_layout or pt.is_parent:  # 垂直 column
                end_x, end_y = start_x + self.parent.__child_max_width__, start_y + self.__draw_height__
            elif pt.is_menu:
                end_x, end_y = start_x + self.parent.__child_max_width__, start_y + self.__draw_height__
            else:
                end_x, end_y = start + self.__draw_size__
        else:
            end_x, end_y = start + self.__draw_size__

        x, y = self.mouse_position
        in_x = start_x < x < end_x
        in_y = start_y < y < end_y
        return in_x and in_y

    @property
    def __child_menu_is_haver__(self) -> bool:
        """子级菜单是否在范围内"""
        offset = self.__offset__ + self.___menu_child_offset_position___ if self.parent else self.offset_position
        start_x, start_y = offset + self.parent_top.__quadrant_translate__
        end_x, end_y = (
            start_x + self.__child_max_width__ + self.layout_margin * 2,
            start_y + self.__child_sum_height__ + self.layout_margin * 2
        )

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
