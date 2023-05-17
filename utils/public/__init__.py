from functools import cache

import bpy
from bpy.types import AddonPreferences, Operator, UILayout

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
            try:
                return self.active_system.selected_children_element[-1]
            except IndexError:
                ...

    @property
    def ui_prop(self):
        return self.pref.ui_property


class CacheHandler(PublicProperty,
                   PublicMethod):
    @classmethod
    def clear_cache(cls):
        cls.pref_.cache_clear()

    @staticmethod
    def tag_redraw(context):
        if context.area:
            context.area.tag_redraw()


class PublicOperator(
    CacheHandler,
    Operator
):
    @staticmethod
    def ops_id_name(string):
        return 'emm_operator.' + string


class TempKey:
    @property
    def keyconfig(self):
        return bpy.context.window_manager.keyconfigs.active

    @property
    def temp_keymaps(self):
        if 'TEMP' not in self.keyconfig.keymaps:
            self.keyconfig.keymaps.new('TEMP')
        return self.keyconfig.keymaps['TEMP']

    def get_temp_kmi(self, idname):
        key = idname
        keymap_items = self.temp_keymaps.keymap_items
        if key not in keymap_items:
            return keymap_items.new(key, 'NONE', 'PRESS')
        return keymap_items[key]


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
