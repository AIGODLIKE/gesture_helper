from functools import cache

from bpy.props import StringProperty
from bpy.types import PropertyGroup


class PublicPropertyGroup(PropertyGroup,
                          ):

    def set_active_index(self, index):
        """需要重写,用作移动时设置列表活动索引
        :param index:
        :return:
        """
        ...

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        """需要重写,获取父集合属性

        :return:
        """
        return object

    @cache
    def _parent_collection_property(self) -> 'PropertyGroup':
        """缓存,父级正常情况下不会变
        :return:
        """
        return self.parent_collection_property

    @classmethod
    def cache_clear_parent_collection_property(cls):
        """清理缓存
        :return:
        """
        cls._parent_collection_property.cache_clear()

    @property
    def items(self) -> 'iter':
        """通过设置父级集合属性拿每一个集㕣元素

        :return:
        """
        return self.parent_collection_property.values()

    @property
    def index(self) -> int:
        """反回当前项在集合属性内的索引"""
        if self in self.items:
            return self.items.index(self)

    def remove(self) -> None:
        """通过索引删除自身
        :return:
        """
        self.parent_collection_property.remove(self.index)

    def move(self, is_next=True):
        """移动此元素在集合内的位置,如果在头或尾部会做处理

        :param is_next: bool ,向下移
        :return:
        """
        le = len(self.items)
        index = self.index
        le1 = le - 1
        next_index = (0 if le1 == index else index + 1) if is_next else (le1 if index == 0 else index - 1)
        self.parent_collection_property.move(index, next_index)

        active_index = le1 if next_index == -1 else next_index
        self.set_active_index(active_index)


class PublicRelationship(PropertyGroup):
    items: iter
    _parent_key = 'parent_name'
    parent_collection_property: PropertyGroup

    def update_parent(self, context):
        self.cache_clear_relationship()

    parent_name: StringProperty(update=update_parent)

    # Parent
    @cache
    def _get_parent_relationship(self):
        try:
            parent = self.parent_collection_property[self.parent_name]
            if self != parent:
                return parent
        except KeyError:
            ...

    def _set_parent_relationship(self, value):
        if type(value) == str:
            self[self._parent_key] = value
        else:
            self[self._parent_key] = value.name
        self.cache_clear_relationship()

    def _del_parent_relationship(self):
        del self[self._parent_key]
        self.cache_clear_relationship()

    def change_name(self, old, new):
        """修改名称时调用此方法,同时修改子级的父项"""
        print('change_name', old, new, self.children)
        for child in self.children:
            child.parent = new

    parent = property(fget=_get_parent_relationship, fset=_set_parent_relationship, fdel=_del_parent_relationship)

    # Child
    @cache
    def _get_children(self) -> 'list':
        return [i for i in self.items if i.parent == self]

    @property
    def children(self) -> 'list':
        return self._get_children()

    @property
    def children_recursion(self) -> 'list':
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.children)
        return children

    @classmethod
    def cache_clear_relationship(cls):
        cls._get_children.cache_clear()
        cls._get_parent_relationship.cache_clear()


class PublicCollectionNoRepeatName(PropertyGroup):
    """
    用来避免名称重复的类,将会代理name属性,如果更改了名称将会判断是否重复,如果重复将会在后缀上加上.001
    需要实例化items函数反回的应是此元素的集合属性,用于遍历所有的元素
    """
    items: 'iter'

    @property
    def _name_keys(self):
        return [i.name for i in self.items]

    @staticmethod
    def _get_suffix(string):
        sp = string.split('.')
        try:
            return int(sp[-1])
        except ValueError as e:
            return -1

    @classmethod
    def _suffix_is_number(cls, string: str) -> bool:
        _i = cls._get_suffix(string)
        if _i == -1 or len(string) < 3:
            return False
        return True

    @property
    def _not_update_name(self):
        return 'name' not in self

    def _get_name(self):
        if self._not_update_name:
            return f'not update name {self}'
        elif 'name' not in self:
            self._set_name('New Name')

        return self['name']

    def _get_effective_name(self, value):

        def _get_number(n):
            if n < 999:
                return f'{n}'.rjust(3, '0')
            return f'1'.rjust(3, '0')

        if value in self._name_keys:
            if self._suffix_is_number(value):
                number = _get_number(self._get_suffix(value) + 1)
                sp = value.split('.')
                sp[-1] = number
                value = '.'.join(sp)
            else:
                value += '.001'
            return self._get_effective_name(value)
        return value

    def _set_name(self, value):
        keys = self._name_keys
        not_update = ('name' in self and value == self['name'] and keys.count(value) < 2)
        if not_update or not value:
            return
        new_name = self._get_effective_name(value)

        old_name = self['name'] if 'name' in self else None

        if getattr(self, 'change_name', False):
            self.change_name(old_name, new_name)
        self['name'] = new_name
        if (len(keys) - len(set(keys))) >= 1:  # 有重复的名称
            raise ValueError('发现重复名称 !!', keys)

    def _update_name(self, context):
        ...

    name: StringProperty(
        name='name',
        get=_get_name,
        set=_set_name,
        update=_update_name,
    )


class TempProperty:
    _temp_key = 'temp_property_gesture'

