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


class ElementIcon:
    icon: StringProperty(name='Show Icon', default='UNKNOWN')
    enabled_icon: BoolProperty(name='Enabled Icon', default=True)

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


# 显示的属性,不用Blender那些,使用自已的参数
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
