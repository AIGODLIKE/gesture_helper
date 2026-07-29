"""Blender background smoke test for persistence and gesture keymap lifecycle."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

GESTURE_IDNAMES = {
    "wm.gesture_operator",
    "wm.gesture_menu",
    "gesture.operator",
}
MANUAL_BINDING = (
    "Window",
    "wm.gesture_operator",
    "Manual User Shortcut",
)


def gesture_bindings() -> Counter:
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    assert keyconfig is not None, "Blender did not create the add-on keyconfig"
    bindings = []
    for keymap in keyconfig.keymaps:
        for item in keymap.keymap_items:
            if item.idname not in GESTURE_IDNAMES:
                continue
            bindings.append((
                keymap.name,
                item.idname,
                getattr(item.properties, "gesture", ""),
            ))
    return Counter(bindings)


def assert_bindings(expected) -> None:
    actual = gesture_bindings()
    expected = Counter(expected)
    assert actual == expected, (actual, expected)


assert bpy.ops.preferences.addon_enable(module="gesture_helper") == {"FINISHED"}

from gesture_helper.gesture.gesture_keymap import GestureKeymap  # noqa: E402
from gesture_helper.preferences import GesturePreferences  # noqa: E402
from gesture_helper.utils.gesture_persistence import (  # noqa: E402
    save_gestures_to_disk,
    suppress_gesture_disk_save,
)
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402


store = get_gesture_store()
assert store is not None

page_ids = tuple(
    item.identifier
    for item in GesturePreferences.bl_rna.properties["show_page"].enum_items
)
assert page_ids == ("GESTURE", "PROPERTY", "BACKUPS", "STYLE"), page_ids
pref = get_pref()
original_page = pref.show_page
pref.show_page = "BACKUPS"
assert pref.show_page == "BACKUPS"
assert callable(getattr(pref, "draw_ui_backups", None))
pref.show_page = original_page

with suppress_gesture_disk_save():
    store.gesture.clear()

    radial = store.gesture.add()
    radial.name = "Lifecycle Radial"
    radial.gesture_type = "RADIAL"
    radial.keymaps = ["Window"]
    radial.key = {"type": "F7", "value": "PRESS"}

    menu = store.gesture.add()
    menu.name = "Lifecycle Menu"
    menu.gesture_type = "MENU"
    menu.keymaps = ["Window"]
    menu.key = {"type": "F8", "value": "PRESS"}

GestureKeymap.key_restart()
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
})

# Registered operators must be siblings, not subclasses of one another. A
# registered parent/child pair leaves bpy.ops pointing at a stale RNA struct.
assert bpy.types.Operator.bl_rna_get_subclass_py(
    "WM_OT_gesture_element_add"
) is not None
assert bpy.types.Operator.bl_rna_get_subclass_py(
    "WM_OT_gesture_layout_preset_add"
) is not None
store.index_gesture = 0
assert bpy.ops.wm.gesture_element_add.poll()
assert bpy.ops.wm.gesture_layout_preset_add.poll()
assert bpy.ops.wm.gesture_element_add(element_type="PROPERTY") == {"FINISHED"}
assert bpy.ops.wm.gesture_layout_preset_add(preset="TOOLBAR") == {"FINISHED"}
radial = next(gesture for gesture in store.gesture if gesture.name == "Lifecycle Radial")
assert [element.element_type for element in radial.element] == ["PROPERTY", "BOX"]

# A shortcut that is not in the add-on's exact ownership registry must survive
# every restart, even when it uses a Gesture Helper operator idname.
addon_keyconfig = bpy.context.window_manager.keyconfigs.addon
window_keymap = addon_keyconfig.keymaps.get("Window")
assert window_keymap is not None
manual_kmi = window_keymap.keymap_items.new(
    "wm.gesture_operator", type="F9", value="PRESS",
)
manual_kmi.properties.gesture = MANUAL_BINDING[-1]
GestureKeymap.key_restart()
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
    MANUAL_BINDING,
})

radial.name = "Lifecycle Radial Renamed"
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
    MANUAL_BINDING,
})

menu.enabled = False
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    MANUAL_BINDING,
})
menu.enabled = True
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
    MANUAL_BINDING,
})

saved_path = save_gestures_to_disk(description="lifecycle_smoke")
assert saved_path and Path(saved_path).is_file(), saved_path

# File > New replaces the SKIP_SAVE WindowManager store. Persistent handlers
# must restore both gesture types and rebuild their matching shortcuts.
assert bpy.ops.wm.read_homefile(use_empty=True) == {"FINISHED"}
store = get_gesture_store()
assert store is not None
restored = {gesture.name: gesture.gesture_type for gesture in store.gesture}
assert restored == {
    "Lifecycle Radial Renamed": "RADIAL",
    "Lifecycle Menu": "MENU",
}, restored
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
    MANUAL_BINDING,
})

# Delete and rebuild: the removed menu shortcut must not survive as an orphan.
menu_index = next(
    index for index, gesture in enumerate(store.gesture)
    if gesture.name == "Lifecycle Menu"
)
with suppress_gesture_disk_save():
    store.gesture.remove(menu_index)
GestureKeymap.key_restart()
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    MANUAL_BINDING,
})

# The artificial add-on-keyconfig KMI has now survived rename, enable/disable,
# File > New, and repeated rebuilds. Remove the smoke-owned item before
# unregistering its operator; Blender does not support orphan add-on KMIs safely.
window_keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.get("Window")
assert window_keymap is not None
manual_items = [
    item
    for item in window_keymap.keymap_items
    if item.idname == MANUAL_BINDING[1] and item.type == "F9"
]
assert len(manual_items) == 1, manual_items
window_keymap.keymap_items.remove(manual_items[0])
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
})

assert bpy.ops.preferences.addon_disable(module="gesture_helper") == {"FINISHED"}
assert not gesture_bindings(), gesture_bindings()

# Re-enable in the same process to exercise class/handler reload safety. The
# preceding unregister saved the post-delete state, so only RADIAL returns.
assert bpy.ops.preferences.addon_enable(module="gesture_helper") == {"FINISHED"}
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
})
assert bpy.types.Operator.bl_rna_get_subclass_py(
    "WM_OT_gesture_element_add"
) is not None
assert bpy.ops.wm.gesture_element_add.poll()

import gesture_helper.register_mod as register_mod  # noqa: E402


def matching_handlers(handlers, callback) -> int:
    return sum(
        register_mod._matches_load_handler(candidate, callback)
        for candidate in handlers
    )


assert matching_handlers(
    bpy.app.handlers.load_pre, register_mod._on_load_pre,
) == 1
assert matching_handlers(
    bpy.app.handlers.load_post, register_mod._on_load_post,
) == 1
animation_pre = getattr(bpy.app.handlers, "animation_playback_pre", None)
animation_post = getattr(bpy.app.handlers, "animation_playback_post", None)
if animation_pre is not None:
    assert matching_handlers(
        animation_pre,
        register_mod._on_animation_playback_transition,
    ) == 1
if animation_post is not None:
    assert matching_handlers(
        animation_post,
        register_mod._on_animation_playback_transition,
    ) == 1

import gesture_helper.utils.ui_draw_sync as ui_draw_sync  # noqa: E402


def pending_modal_refresh():
    return None


bpy.app.timers.register(pending_modal_refresh, first_interval=60.0)
ui_draw_sync._modal_ui_refresh_fn = pending_modal_refresh
ui_draw_sync._playback_panel_snapshots[123] = (
    ui_draw_sync._PanelContentSnapshot()
)
register_mod._on_animation_playback_transition()
assert ui_draw_sync._modal_ui_refresh_fn is None
assert not bpy.app.timers.is_registered(pending_modal_refresh)
assert not ui_draw_sync._playback_panel_snapshots

assert bpy.ops.preferences.addon_disable(module="gesture_helper") == {"FINISHED"}
assert not gesture_bindings(), gesture_bindings()
assert matching_handlers(
    bpy.app.handlers.load_pre, register_mod._on_load_pre,
) == 0
assert matching_handlers(
    bpy.app.handlers.load_post, register_mod._on_load_post,
) == 0
if animation_pre is not None:
    assert matching_handlers(
        animation_pre,
        register_mod._on_animation_playback_transition,
    ) == 0
if animation_post is not None:
    assert matching_handlers(
        animation_post,
        register_mod._on_animation_playback_transition,
    ) == 0

print(f"LIFECYCLE_SMOKE_OK Blender {bpy.app.version_string}")
