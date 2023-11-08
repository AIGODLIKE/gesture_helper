from bpy.props import EnumProperty, BoolProperty, CollectionProperty, IntProperty

from ...enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE, ENUM_RELATIONSHIP, ENUM_GESTURE_DIRECTION


class ElementAddProperty:
    relationship: EnumProperty(
        name='关系',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )

    element_type: EnumProperty(
        name='类型',
        default='ELEMENT',
        items=ENUM_ELEMENT_TYPE,
    )
    selected_type: EnumProperty(
        name='选择结构类型',
        default='IF',
        items=ENUM_SELECTED_TYPE,
    )

    @property
    def is_element(self) -> bool:
        return self.element_type == 'ELEMENT'

    @property
    def is_selected_structure(self) -> bool:
        return self.element_type == 'SELECTED_STRUCTURE'


# 显示的属性,不用Blender那些,使用自已的参数
class ElementDirectionProperty(ElementAddProperty):
    gesture_direction: EnumProperty(
        name='手势方向',
        default='1',
        items=ENUM_GESTURE_DIRECTION,
    )


class ElementProperty(ElementDirectionProperty):
    collection: CollectionProperty
    enabled: BoolProperty(name='启用', default=True)

    show_child: BoolProperty(name='显示子级', default=True)
    as_child: BoolProperty(
        name='作为子级',
        default=False
    )
    level: IntProperty(name="TODO Element Relationship Level", default=0)
