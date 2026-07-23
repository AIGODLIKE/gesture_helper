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
from gesture_helper.utils.gesture_persistence import (  # noqa: E402
    save_gestures_to_disk,
    suppress_gesture_disk_save,
)
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402


store = get_gesture_store()
assert store is not None

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

# A shortcut left by an interrupted old release must be removed without
# disturbing the current RADIAL/MENU pair.
addon_keyconfig = bpy.context.window_manager.keyconfigs.addon
window_keymap = addon_keyconfig.keymaps.get("Window")
assert window_keymap is not None
window_keymap.keymap_items.new(
    "gesture.operator", type="F9", value="PRESS",
)
GestureKeymap.key_restart()
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
})

radial.name = "Lifecycle Radial Renamed"
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
})

menu.enabled = False
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
})
menu.enabled = True
assert_bindings({
    ("Window", "wm.gesture_operator", "Lifecycle Radial Renamed"),
    ("Window", "wm.gesture_menu", "Lifecycle Menu"),
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

assert bpy.ops.preferences.addon_disable(module="gesture_helper") == {"FINISHED"}
assert not gesture_bindings(), gesture_bindings()
assert matching_handlers(
    bpy.app.handlers.load_pre, register_mod._on_load_pre,
) == 0
assert matching_handlers(
    bpy.app.handlers.load_post, register_mod._on_load_post,
) == 0

print(f"LIFECYCLE_SMOKE_OK Blender {bpy.app.version_string}")
