from bpy.props import EnumProperty, BoolProperty, CollectionProperty, IntProperty
from bpy.app.translations import pgettext as _
from ...enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE, ENUM_RELATIONSHIP, ENUM_GESTURE_DIRECTION
from ...public import get_pref
from ...public_cache import PublicCacheFunc, cache_update_lock


class ElementAddProperty:
    relationship: EnumProperty(
        name='relationship',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )
    element_type: EnumProperty(
        name='type',
        default='CHILD_GESTURE',
        items=ENUM_ELEMENT_TYPE,
    )

    @staticmethod
    @cache_update_lock
    def update_selected_type():
        PublicCacheFunc.cache_clear()

    selected_type: EnumProperty(
        name='selection structure type',
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


# 显示的属性,不用Blender那些,使用自已的参数
class ElementDirectionProperty(ElementAddProperty):
    direction: EnumProperty(
        name='direction',
        items=ENUM_GESTURE_DIRECTION,
        default='8'
    )

    def init_child_gesture(self):
        self.init_direction_by_sort()
        self.selected_type = 'IF'


class ElementProperty(ElementDirectionProperty):
    collection: CollectionProperty
    enabled: BoolProperty(name=_('enable'), default=True, update=lambda self, context: self.cache_clear())

    show_child: BoolProperty(name=_('displays the children'), default=False)
    level: IntProperty(name=_("Element Relationship Level"), default=0)
