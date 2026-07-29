"""Verify the built ZIP from an isolated Blender extension repository."""

from __future__ import annotations

import importlib
import os

import bpy


REPOSITORY = os.environ.get("GH_TEST_REPOSITORY", "gh_test")
PACKAGE_ID = os.environ.get("GH_TEST_PACKAGE_ID", "gesture_helper")
PACKAGE = f"bl_ext.{REPOSITORY}.{PACKAGE_ID}"
EXPECTED_VERSION = tuple(
    int(part)
    for part in os.environ.get("GH_EXPECTED_EXTENSION_VERSION", "2.4.0").split(".")
)
EXPECTED_PRESET_COUNT = int(os.environ.get("GH_EXPECTED_PRESET_COUNT", "12"))

assert PACKAGE in bpy.context.preferences.addons, tuple(bpy.context.preferences.addons.keys())
extension = importlib.import_module(PACKAGE)
assert extension.ADDON_VERSION == EXPECTED_VERSION, (
    extension.ADDON_VERSION,
    EXPECTED_VERSION,
)

element_module = importlib.import_module(f"{PACKAGE}.element")
element_types = {
    item.identifier
    for item in element_module.Element.bl_rna.properties["element_type"].enum_items
}
assert "SPLIT" in element_types, element_types

gesture_cure = importlib.import_module(f"{PACKAGE}.ops.gesture_cure")
gesture_store = importlib.import_module(f"{PACKAGE}.utils.gesture_store")
store = gesture_store.get_gesture_store()
assert store is not None
store.gesture.clear()
assert gesture_cure.add_all_preset() == EXPECTED_PRESET_COUNT
assert len(store.gesture) > 0

assert bpy.ops.preferences.addon_disable(module=PACKAGE) == {"FINISHED"}
print(
    "INSTALLED_EXTENSION_SMOKE_OK "
    f"Blender {bpy.app.version_string} {PACKAGE} {EXPECTED_VERSION}"
)
