from bpy.props import EnumProperty, BoolProperty, CollectionProperty, IntProperty

from ...enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE, ENUM_RELATIONSHIP, ENUM_GESTURE_DIRECTION
from ...public import get_pref


class ElementAddProperty:
    relationship: EnumProperty(
        name='关系',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )
    element_type: EnumProperty(
        name='类型',
        default='CHILD_GESTURE',
        items=ENUM_ELEMENT_TYPE,
    )
    selected_type: EnumProperty(
        name='选择结构类型',
        items=ENUM_SELECTED_TYPE,
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


# 显示的属性,不用Blender那些,使用自已的参数
class ElementDirectionProperty(ElementAddProperty):
    direction: EnumProperty(
        name='方向',
        items=ENUM_GESTURE_DIRECTION,
        default='8'
    )

    def init_child_gesture(self):
        self.init_direction_by_sort()
        self.selected_type = 'IF'


class ElementProperty(ElementDirectionProperty):
    collection: CollectionProperty
    enabled: BoolProperty(name='启用', default=True, update=lambda self, context: self.cache_clear())

    show_child: BoolProperty(name='显示子级', default=True)
    level: IntProperty(name="Element Relationship Level", default=0)
