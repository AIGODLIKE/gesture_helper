"""Add-on preferences access with register-cycle caching."""

from __future__ import annotations

from os.path import abspath, dirname, join, realpath

import bpy

ADDON_FOLDER = dirname(dirname(realpath(__file__)))
PRESET_FOLDER = abspath(join(ADDON_FOLDER, 'src', 'preset'))

_PREF = None


def get_pref():
    """Return add-on preferences; cached for the current register cycle."""
    global _PREF
    if _PREF is not None:
        return _PREF
    from .. import __package__ as base_package
    _PREF = bpy.context.preferences.addons[base_package].preferences
    return _PREF


def clear_pref_cache() -> None:
    """Drop the preferences cache (call on register/unregister/load)."""
    global _PREF
    _PREF = None


def poll_addon_preferences(cls) -> bool:
    try:
        get_pref()
    except (KeyError, AttributeError):
        cls.poll_message_set("Add-on is not enabled")
        return False
    return True


def poll_message_active_gesture(cls) -> bool:
    if not poll_addon_preferences(cls):
        return False
    if get_pref().active_gesture is None:
        cls.poll_message_set("No active gesture")
        return False
    return True


def poll_message_active_element(cls) -> bool:
    if not poll_addon_preferences(cls):
        return False
    if get_pref().active_element is None:
        cls.poll_message_set("No active element")
        return False
    return True
