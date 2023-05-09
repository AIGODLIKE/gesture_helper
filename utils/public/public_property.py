from functools import cache

from bpy.props import StringProperty
from bpy.types import PropertyGroup


class IntFaceProp:
    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        return object

    @cache
    def _parent_collection_property(self) -> 'PropertyGroup':
        return self.parent_collection_property

    @classmethod
    def cache_clear_parent_collection_property(cls):
        cls._parent_collection_property.cache_clear()


class PublicPropertyGroup(PropertyGroup,
                          IntFaceProp,
                          ):

    @property
    def items(self) -> 'iter':
        return self.parent_collection_property.values()

    @property
    def index(self) -> int:
        if self in self.items:
            return self.items.index(self)

    def remove(self):
        self.parent_collection_property.remove(self.index)

    def move(self, is_next=True):
        le = len(self.items)
        index = self.index
        le1 = le - 1
        next_index = (0 if le1 == index else index + 1) if is_next else (le1 if index == 0 else index - 1)
        self.parent_collection_property.move(index, next_index)

        active_index = le1 if next_index == -1 else next_index
        self.set_active_index(active_index)

    def set_active_index(self, index):
        ...

    def copy(self):
        ...


class PublicNoRepeatName:
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

    def chick_name(self):
        # for key in self._name_keys:
        #     self._items[key]._set_name(key)
        ...

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
        name = self._get_effective_name(value)

        old_name = self['name'] if 'name' in name else None

        self['name'] = name

        if getattr(self, 'change_name', False):
            self.change_name(old_name, name)
        if (len(keys) - len(set(keys))) >= 1:  # 有重复的名称
            self.chick_name()

    def change_name(self, old_name, new_name):
        ...

    def set_name(self, name):
        self['name'] = self.name = name

    def _update_name(self, context):
        ...

    name: StringProperty(
        name='name',
        get=_get_name,
        set=_set_name,
        update=_update_name,
    )
