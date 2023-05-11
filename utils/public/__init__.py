from functools import cache

import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences, UILayout, Operator

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
    def systems(self):
        return self.pref.systems

    @property
    def active_system(self):
        index = self.pref.active_index
        try:
            return self.systems[index]
        except IndexError:
            ...

    @property
    def active_ui_element(self):
        """
        :return: UiElement
        """
        if self.active_system:
            index = self.active_system.active_index
            try:
                return self.active_system.ui_element[index]
            except IndexError:
                ...

    @property
    def ui_prop(self):
        return self.pref.ui_property


class CacheHandler(PublicProperty):
    @classmethod
    def clear_cache(cls):
        cls.pref_.cache_clear()


class PublicOperator(
    CacheHandler,
    Operator
):
    @staticmethod
    def ops_id_name(string):
        return 'emm_operator.' + string


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
