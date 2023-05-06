from functools import cache
from os.path import basename, dirname, realpath

import bpy
from bpy_types import AddonPreferences
from bpy.types import UILayout


class Preferences:
    G_ADDON_NAME = basename(dirname(realpath(__file__)))

    @staticmethod
    @cache
    def pref_() -> 'AddonPreferences':
        return bpy.context.preferences.addons[Preferences.G_ADDON_NAME].preferences

    @property
    def pref(self) -> 'AddonPreferences':
        return Preferences.pref_()


class CacheHandler(Preferences):
    @classmethod
    def clear_cache(cls):
        cls.pref_.cache_clear()


class PublicClass(CacheHandler):
    layout: UILayout
    ...
