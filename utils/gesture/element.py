from functools import cache

import bpy
from bpy.props import EnumProperty, StringProperty, BoolProperty, FloatProperty, IntProperty
from bpy.types import PropertyGroup

from ..log import log
from ..property import ui_emboss_enum, ui_alignment, ui_direction, CUSTOM_UI_TYPE_ITEMS, UI_ELEMENT_TYPE_ENUM_ITEMS, \
    UI_ELEMENT_SELECT_STRUCTURE_TYPE, SELECT_STRUCTURE
from ..utils import PublicClass, PublicName, PublicMove


class UiElement(PropertyGroup,
                PublicName,
                PublicClass,
                PublicMove
                ):
    ...


class ElementProperty(UiElement):
    @property
    def _items(self):
        return self.ui_element_items[self._parent_element_key]

    default_float = {'min': 0,
                     'soft_max': 20,
                     'soft_min': 0.15,
                     }
    activate_init: BoolProperty()
    active: BoolProperty()
    scale_x: FloatProperty(**default_float)
    scale_y: FloatProperty(**default_float)
    ui_units_x: FloatProperty(**default_float)
    ui_units_y: FloatProperty(**default_float)
    active_default: BoolProperty()

    alert: BoolProperty()
    use_property_decorate: BoolProperty()
    use_property_split: BoolProperty(name='使用属性拆分')

    emboss_enum: EnumProperty(name='emboss enum',
                              description='有两个emboss 这个用于UILayout的输入枚举项',
                              **ui_emboss_enum,
                              default='NORMAL')
    enabled: BoolProperty(name='启用')

    alignment: EnumProperty('对齐模式', **ui_alignment)
    direction: EnumProperty(name='方向', **ui_direction)

    # UILayout property

    def _update_text(self, context):
        self._by_text_set_name()

    text: StringProperty(name='文字', default='text', update=_update_text)

    # enum
    # ctext: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
    # text_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
    # heading_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')

    # int
    columns: IntProperty()

    row_major: IntProperty()

    toggle: IntProperty(name='切换',
                        max=1, min=-1, default=1)

    # float

    factor: FloatProperty(name='系数',
                          min=0.01,
                          max=100,
                          soft_max=0.8,
                          soft_min=0.1,
                          step=0.01,
                          default=0.5)

    # bool
    def _update_heading(self, context):
        """更新标题文字
        并自动更新元素名称

        Args:
            context (_type_): _description_
        """

        self._by_heading_set_name()

    align: BoolProperty(name='对齐')
    heading: StringProperty(name='标题', update=_update_heading)
    translate: BoolProperty(name='翻译文字')
    invert_checkbox: BoolProperty(name='反转复选框')
    emboss: BoolProperty(name='浮雕')

    expand: BoolProperty(name='扩展')

    slider: BoolProperty()

    depress: BoolProperty()

    even_columns: BoolProperty()
    even_rows: BoolProperty()


class RelationProperty(ElementProperty):
    def move(self, is_next=True):
        parent = self.parent_element
        col = parent.ui_items_collection_group

        self.move_collection_element(col,
                                     parent,
                                     is_next=is_next)
        self.check_parent_element()

    def check_parent_element(self):
        """找父级元素,如果没有的话"""
        if self._parent_element_key not in self.element_items:
            for i in self.element_items:
                if self in i.ui_items_collection_group.values():
                    self[self._parent_element_key] = i['name']

    @property
    def parent_element(self):  # 反回父级元素,如果没有直接报错
        return self.element_items[self._parent_element_name]

    @property
    def _parent_element_name(self):
        if self._parent_element_key not in self:
            self.check_parent_element()
        return self[self._parent_element_key]

    @property
    @cache
    def children(self):  # 迭代子级ui
        if self._child_ui_key in self:
            # return [(i, *i.child_ui) for i in self.child_ui]
            re = []
            for i in self.child_ui:
                re.append(i)
                re.extend(i.child_ui)
            return re

    @property
    @cache
    def child(self):  # 子级ui
        return [ui for ui in self.parent_element.ui_items_collection_group if
                self in self._child_ui_key and ui.name in self[self._child_ui_key]]

    @cache
    def _get_parent(self):
        if self._parent_ui_key in self:
            key = self[self._parent_ui_key]
            return self.parent_element.ui_items_collection_group[key]

    def _set_parent(self, value: str):
        self._get_parent.cache_clear()
        if self.parent_element.ui_items_collection_group.get(value):
            self[self._parent_ui_key] = value
            log.info(f'{self} set parent {value}')
        else:
            log.debug(f'{self} set parent error not find {value}')

    parent = property(_get_parent, _set_parent, )

    @staticmethod
    @cache
    def get_level(self):
        return -1

    @property
    def level(self) -> int:
        return self.get_level(self)

    @classmethod
    def clear_element_cache(cls):
        cls.get_level.cache_clear()
        cls._get_parent.cache_clear()


class UiCollectionGroupElement(RelationProperty):  # ui项
    ui_element_type: EnumProperty(items=UI_ELEMENT_TYPE_ENUM_ITEMS + UI_ELEMENT_SELECT_STRUCTURE_TYPE, )

    @property
    def is_select_structure(self):
        return self.ui_element_type.lower() in SELECT_STRUCTURE

    def remove(self):
        self.parent_element.ui_items_collection_group.remove(self._index)

    def copy(self):
        new = self.parent_element.ui_items_collection_group.add()
        new[self._parent_element_key] = self._parent_element_name
        new.set_name(self.name)

    def move_to(self, to):
        ...

    @property
    def _items(self):
        self.check_parent_element()
        key = self[self._parent_element_key]
        return self.element_items[key].ui_items_collection_group

    @property
    def _index(self):
        return self.parent_element.ui_items_collection_group.values().index(self)

    def refresh_children(self):
        ...

    def register_key(self):
        ...

    def unregister_key(self):
        ...


class_tuple = (
    UiElement,

    UiCollectionGroupElement,
)

register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
