"""Session gesture tree accessors (WindowManager store, not userpref)."""

from __future__ import annotations

import bpy

WM_STORE_ATTR = "gesture_helper"


def get_gesture_store():
    """Return the WM GestureStore, or None when unavailable."""
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return None
    return getattr(wm, WM_STORE_ATTR, None)


def get_gestures():
    """Return the session gesture CollectionProperty, or None."""
    store = get_gesture_store()
    if store is None:
        return None
    return store.gesture
