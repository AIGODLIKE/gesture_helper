"""Preference accessors shared by UI / operators / PropertyGroups."""

from __future__ import annotations


class PrefAccess:
    """Thin access to add-on preferences PropertyGroups."""

    @staticmethod
    def _pref():
        from .pref import get_pref
        return get_pref()

    @property
    def pref(self):
        return self._pref()

    @property
    def draw_property(self):
        return self._pref().draw_property

    @property
    def debug_property(self):
        return self._pref().debug_property

    @property
    def backups_property(self):
        return self._pref().backups_property

    @property
    def other_property(self):
        return self._pref().other_property

    @property
    def gesture_property(self):
        return self._pref().gesture_property

    @property
    def is_debug(self) -> bool:
        from .debug_util import get_debug
        return get_debug()
