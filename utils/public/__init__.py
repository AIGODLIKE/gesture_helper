from functools import cache
from os.path import basename, dirname, realpath

import bpy
from bpy.types import UILayout, AddonPreferences

from .public_data import PublicData
from .public_func import PublicMethod


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


class PublicClass(CacheHandler, PublicData, PublicMethod):
    layout: UILayout
