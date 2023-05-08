from functools import cache

import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences, UILayout

from .public_data import PublicData
from .public_func import PublicMethod


class PublicProperty:
    @staticmethod
    @cache
    def pref_() -> 'AddonPreferences':
        return bpy.context.preferences.addons[PublicData.G_ADDON_NAME].preferences

    @property
    def pref(self) -> 'AddonPreferences':
        return PublicProperty.pref_()

    @property
    def ui_system(self) -> '[SystemItem]':
        return self.pref.ui_system

    @property
    def active_system(self) -> 'SystemItem':
        index = self.pref.active_index
        try:
            return self.ui_system[index]
        except IndexError:
            ...

    @property
    def active_ui_element(self) -> 'UiElement':
        """
        :return: UiElement
        """
        if self.active_system:
            index = self.active_system.active_index
            try:
                return self.active_system.ui_element[index]
            except IndexError:
                ...


class CacheHandler(PublicProperty):
    @classmethod
    def clear_cache(cls):
        cls.pref_.cache_clear()



class PublicName:
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
        # for key in self._keys:
        #     self._items[key]._set_name(key)
        ...

    def _get_effective_name(self, value):

        def _get_number(n):
            if n < 999:
                return f'{n}'.rjust(3, '0')
            return f'1'.rjust(3, '0')

        if value in self._keys:
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
        keys = self._keys
        not_update = ('name' in self and value == self['name'] and keys.count(value) < 2)
        if not_update or not value:
            log.debug(f'not_set name\t"{self["name"]}" value to\t"{value}"')
            return
        name = self._get_effective_name(value)

        log.debug(f'set name \'{name}\'')
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

class PublicClass(
    CacheHandler,
):
    layout: UILayout


def register_module_factory(module):
    is_debug = False

    def reg():
        for mod in module:
            if is_debug:
                print('register ', mod)
            mod.register()

    def un_reg():
        for mod in reversed(module):
            if is_debug:
                print('unregister ', mod)
            mod.unregister()

    return reg, un_reg
