from functools import cache
from os.path import dirname, basename, realpath
from bpy.types import Operator
import bpy

ADDON_NAME = basename(dirname(dirname(realpath(__file__))))


class PublicCacheData:
    @staticmethod
    @cache
    def _pref():
        return bpy.context.preferences.addons[ADDON_NAME].preferences

    @staticmethod
    def clear_cache():
        PublicCacheData.clear_cache()


class PublicProperty(PublicCacheData):
    @property
    def pref(self):
        return self._pref()

    @property
    def active_gesture(self):
        index = self.pref.gesture_index
        try:
            return self.pref.gesture[index]
        except IndexError:
            return

    @property
    def active_element(self):
        try:
            return self.active_gesture.element[self.active_gesture.element_index]
        except IndexError:
            return


class PublicOperator(Operator, PublicProperty):
    ...
