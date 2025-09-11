from bpy.props import EnumProperty, BoolProperty, CollectionProperty, IntProperty, StringProperty

from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE, ENUM_RELATIONSHIP, ENUM_GESTURE_DIRECTION
from ..utils.public import get_pref
from ..utils.public_cache import PublicCacheFunc, cache_update_lock


class ElementAddProperty:
    relationship: EnumProperty(
        name='Relationship',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )
    element_type: EnumProperty(
        name='Type',
        default='CHILD_GESTURE',
        items=ENUM_ELEMENT_TYPE,
    )

    add_active_radio: BoolProperty(name="Whether or not to set it as an active item when adding an element",
                                   default=False)

    @staticmethod
    @cache_update_lock
    def update_selected_type():
        PublicCacheFunc.cache_clear()

    selected_type: EnumProperty(
        name='Select structure type',
        items=ENUM_SELECTED_TYPE,
        update=lambda self, context: ElementAddProperty.update_selected_type()
    )

    @property
    def is_selected_structure(self) -> bool:
        return self.element_type == 'SELECTED_STRUCTURE'

    @property
    def is_child_gesture(self) -> bool:
        return self.element_type == 'CHILD_GESTURE'

    @property
    def is_operator(self) -> bool:
        return self.element_type == 'OPERATOR'

    @property
    def is_child_relationship(self) -> bool:
        return self.relationship == 'CHILD'

    @property
    def is_have_add_child(self) -> bool:
        """是可添加的子级
        @return: bool
        """
        pref = get_pref()
        act = pref.active_element
        is_operator = act and act.is_operator
        return not (is_operator and pref.add_element_property.is_child_relationship)

    @property
    def is_selected_if(self) -> bool:
        return self.selected_type == 'IF'

    @property
    def is_selected_elif(self) -> bool:
        return self.selected_type == 'ELIF'

    @property
    def is_selected_else(self) -> bool:
        return self.selected_type == 'ELSE'

    @property
    def parent_is_extension(self) -> bool:  # 父级是扩展项,就是底部的菜单
        pe = self.parent_element
        if pe:
            if pe.parent_is_extension:
                return True
            if pe.direction == "9":
                return True
        return False

    @property
    def extension_by_child_is_hover(self) -> bool:
        """此项是显示为扩展子级并且是hover悬停"""
        ops = getattr(self, "ops", None)
        area = getattr(self, "extension_by_child_draw_area", None)
        if ops and area:
            x1, y1, x2, y2 = area
            x, y = ops.event.mouse_region_x, ops.event.mouse_region_y
            return x1 < x < x2 and y1 < y < y2
        return False

    @property
    def mouse_is_in_extension_area(self) -> bool:
        """鼠标是在扩展区域的
        当前扩展的子级绘制区域
        """
        item = getattr(self, "extension_draw_area", None)
        if item:
            x1, y1, x2, y2 = item
            x, y = self.ops.event.mouse_region_x, self.ops.event.mouse_region_y
            return x1 < x < x2 and y1 < y < y2
        return False


class ElementIcon:
    icon: StringProperty(name='Show Icon', default='COLOR_ERROR')
    enabled_icon: BoolProperty(name='Enabled Icon', default=False)

    @property
    def is_have_icon(self):
        """是可以显示图标的类型
        只有操作符和子手势可以显示图标
        """
        return self.is_operator or self.is_child_gesture

    @property
    def all_icons(self) -> list[str]:
        from ..utils.icons import get_all_icons
        return get_all_icons()

    @property
    def icon_is_validity(self) -> bool:
        """图标是有效的"""
        return self.icon in self.all_icons

    @property
    def is_show_icon(self) -> bool:
        """是可以显示图标的"""
        return self.enabled_icon and self.icon_is_validity

    @property
    def is_draw_icon(self):
        """是绘制图标"""
        return self.is_have_icon and self.is_show_icon

    @property
    def is_draw_child_icon(self):
        """是绘制子级的标识图标"""
        return get_pref().draw_property.element_draw_child_icon and self.is_child_gesture


# 显示的属性, 不用Blender那些, 使用自已的参数
class ElementDirectionProperty(ElementAddProperty):
    direction: EnumProperty(
        name='Direction',
        items=ENUM_GESTURE_DIRECTION,
        default='8'
    )

    def __init_child_gesture__(self):
        self.__init_direction_by_sort__()
        self.selected_type = 'IF'


class ElementProperty(ElementDirectionProperty, ElementIcon):
    collection: CollectionProperty
    enabled: BoolProperty(name='Enabled', default=True, update=lambda self, context: self.cache_clear())

    show_child: BoolProperty(name='Show child', default=False)
    level: IntProperty(name="Element Relationship Level", default=0)
