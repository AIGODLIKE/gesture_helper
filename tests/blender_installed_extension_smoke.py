"""Verify the built ZIP from an isolated Blender extension repository."""

from __future__ import annotations

import importlib

import bpy


PACKAGE = "bl_ext.gh_test.gesture_helper"

assert PACKAGE in bpy.context.preferences.addons, tuple(bpy.context.preferences.addons.keys())
extension = importlib.import_module(PACKAGE)
assert extension.ADDON_VERSION == (2, 4, 0), extension.ADDON_VERSION

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
assert gesture_cure.add_all_preset() == 11
assert len(store.gesture) > 0

assert bpy.ops.preferences.addon_disable(module=PACKAGE) == {"FINISHED"}
print(f"INSTALLED_EXTENSION_SMOKE_OK Blender {bpy.app.version_string}")
