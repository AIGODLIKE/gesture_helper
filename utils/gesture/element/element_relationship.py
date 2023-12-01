from functools import cache

from bpy.props import BoolProperty

from ...public import (PublicSortAndRemovePropertyGroup, PublicUniqueNamePropertyGroup)
from ...public_cache import PublicCache


@cache
def get_available_selected_structure(element) -> bool:
    def get_prev(e):
        p = e.prev_element
        if p and not p.enabled:
            return get_prev(p)
        else:
            return p

    prev = get_prev(element)  # 上一个,如果上一个是禁用的就拿上一个的上一个
    prev_type = getattr(prev, 'selected_type', None)  # 上一个类型

    if not element.is_selected_structure:
        return False
    elif element.is_selected_if:
        return element.enabled
    elif element.is_selected_elif or element.is_selected_else:
        if prev_type:
            # 不是 else即正确 并且这个元素是启用的
            return not prev.is_selected_else and prev.is_available_selected_structure and element.enabled
        else:
            return False
    else:
        print('例外', element)
    return False


class Relationship:
    @property
    def parent(self):
        pe = self.parent_element
        if pe:
            return pe
        else:
            return self.parent_gesture

    @property
    def parent_element(self):
        return PublicCache.__element_parent_element_cache__[self]

    @property
    def parent_gesture(self):
        return PublicCache.__element_parent_gesture_cache__[self]

    @property
    def collection_iteration(self) -> list:
        items = []
        for element in self.parent_gesture.element:
            items.extend(PublicCache.__element_child_iteration__[element])
        return items

    @property
    def collection(self):
        pe = self.parent_element
        if pe:
            return pe.element
        else:
            return self.parent_gesture.element

    @property
    def element_iteration(self):
        return PublicCache.__gesture_element_iteration__[self.parent_gesture]

    @property
    def prev_element(self):
        return PublicCache.__element_prev_cache__[self]

    @property
    def gesture_direction_items(self):
        return self.get_gesture_direction_items(self.element)

    @property
    def parent_gesture_direction_items(self):
        return self.parent.gesture_direction_items


class RadioSelect:

    def update_radio(self, context):
        for item in self.radio_iteration:
            is_select = item == self
            item['radio'] = is_select
            if is_select and self.is_operator:  # 是操作符的话就更新一下kmi
                self.to_operator_tmp_kmi()


    radio: BoolProperty(name='单选',
                        update=update_radio)

    @property
    def radio_iteration(self):
        return self.parent_gesture.element_iteration


class ElementRelationship(PublicUniqueNamePropertyGroup,
                          RadioSelect,
                          PublicSortAndRemovePropertyGroup,
                          Relationship):

    def _get_index(self) -> int:
        return self.parent.index_element

    def _set_index(self, value):
        self.parent.index_element = value

    index = property(
        fget=_get_index,
        fset=_set_index,
        doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def is_root(self):
        return self in self.parent_gesture.element.values()

    def selected_update(self, context):
        """
        在选择其它子项的时候自动将活动索引切换
        @rtype: object
        """
        if self.is_root:
            for (index, element) in enumerate(self.parent_gesture.element):
                if self in element.collection_iteration:
                    self.parent_gesture['index_element'] = self.index

    @property
    def names_iteration(self):
        return self.parent_gesture.element_iteration

    # TODO Remove move active index

    @property
    def is_available_selected_structure(self) -> bool:  # 是一个可用的选择结构
        return get_available_selected_structure(self)

    @property
    def is_show_alert(self) -> bool:
        if self.is_selected_structure:  # 选择结构
            if self.enabled:  # 启用了的
                return not self.is_available_selected_structure
            # 没启用的话就不过这个逻辑
        elif self.is_operator:
            return not self.is_available_operator
        # elif self.is_child_gesture:
        #     return self.

        return False

    @property
    def is_available_poll(self) -> bool:  # 是一个可用的poll
        try:
            self.poll_bool
            return True
        except Exception as e:
            return False

    @property
    def is_available_operator(self) -> bool:  # 是一个可用的操作符
        try:
            self.properties
            self.operator_func
            return True
        except Exception as e:
            return False

    def init_direction_by_sort(self):
        """初始化方向按排序"""
        ds = list(self.parent_gesture_direction_items.keys())
        for k in range(1, 9):
            s = str(k)
            if s not in ds:
                self.direction = s
                return
