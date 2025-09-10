from functools import cache

from bpy.props import BoolProperty, StringProperty

from ..utils.public import (PublicSortAndRemovePropertyGroup, get_gesture_direction_items)
from ..utils.public_cache import PublicCache, cache_update_lock


@cache
def get_element_index(element) -> int:
    try:
        return element.collection.values().index(element)
    except ValueError:
        ...


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
        # 上一个不是选择结构
        return False
    elif element.is_selected_if:
        # 上一个是选择结构if
        return element.enabled
    elif element.is_selected_elif or element.is_selected_else:
        if prev_type:
            # 不是 else即正确 并且这个元素是启用的
            return not prev.is_selected_else and prev.__selected_structure_is_validity__ and element.enabled
        else:
            return False
    else:
        Exception('例外', element)
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
    def root_parent(self):
        if self.is_root:
            return self
        else:
            return self.parent_element.root_parent

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
        """反回当前手势的所有项"""
        return PublicCache.__gesture_element_iteration__[self.parent_gesture]

    @property
    def prev_element(self):
        return PublicCache.__element_prev_cache__[self]

    @property
    def gesture_direction_items(self):
        return get_gesture_direction_items(self.element)

    @property
    def parent_gesture_direction_items(self):
        return self.parent.gesture_direction_items

    @property
    def element_child_iteration(self):
        return PublicCache.__element_child_iteration__[self]


class RadioSelect:

    @cache_update_lock
    def update_radio(self):
        try:
            for (index, element) in enumerate(self.parent_gesture.element):
                if self.root_parent == element:
                    self.parent_gesture.index_element = index

            if not self.is_root:  # 设置子级手势的索引
                for index, e in enumerate(self.collection):
                    if e == self:
                        self.parent.index_element = index

            for item in self.radio_iteration:
                is_select = item == self
                item['radio'] = is_select
                if is_select and self.is_operator:  # 是操作符的话就更新一下kmi
                    self.to_operator_tmp_kmi()
        except Exception as e:
            self.cache_clear()
            print(e.args)
            import traceback
            traceback.print_exc()
            traceback.print_stack()

    radio: BoolProperty(name='Radio', update=lambda self, context: self.update_radio())

    @property
    def radio_iteration(self):
        return self.parent_gesture.element_iteration


class ElementRelationship(RadioSelect,
                          PublicSortAndRemovePropertyGroup,
                          Relationship):
    name: StringProperty(name="Name")

    def _get_index(self) -> int:
        return self.parent.index_element

    def _set_index(self, value):
        self.parent.index_element = value

    index = property(
        fget=_get_index,
        fset=_set_index,
        doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def self_index(self):
        return get_element_index(self)

    @property
    def is_root(self):
        return self in self.parent_gesture.element.values()

    @property
    def names_iteration(self):
        return self.parent_gesture.element_iteration

    @property
    def is_alert(self) -> bool:
        """是显示警告的UI"""
        if self.is_selected_structure:  # 选择结构
            # 是一个可用的选择结构
            if self.enabled:
                return not self.__selected_structure_is_validity__
        elif self.is_operator:
            if self.operator_type == "OPERATOR":
                return not (self.__operator_id_name_is_validity__ and self.__operator_properties_is_validity__)
        return False

    @property
    def __selected_structure_is_validity__(self) -> bool:
        """是一个可用的选择结构"""
        return get_available_selected_structure(self) and self.__poll_bool_is_validity__

    def remove_after(self):
        """删除之后判断索引是否需要偏移"""
        print('remove_after', self)
        parent = self.parent
        index = parent.index_element
        col = self.collection
        cl = len(col)
        if cl:
            if cl >= index + 1:
                col[index].radio = True
            else:
                col[-1].radio = True

    def __init_direction_by_sort__(self):
        """初始化方向按排序"""
        ds = list(self.parent_gesture_direction_items.keys())
        for k in range(1, 9):
            s = str(k)
            if s not in ds:
                self.direction = s
                return
