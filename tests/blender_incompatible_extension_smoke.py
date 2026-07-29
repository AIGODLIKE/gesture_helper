"""Verify that an extension requiring a newer Blender was not installed."""

from __future__ import annotations

import importlib.util
import os

import bpy


REPOSITORY = os.environ.get("GH_TEST_REPOSITORY", "gh_test")
PACKAGE_ID = os.environ.get("GH_TEST_PACKAGE_ID", "gesture_helper")
PACKAGE = f"bl_ext.{REPOSITORY}.{PACKAGE_ID}"

assert PACKAGE not in bpy.context.preferences.addons, tuple(
    bpy.context.preferences.addons.keys()
)
try:
    package_spec = importlib.util.find_spec(PACKAGE)
except ModuleNotFoundError:
    package_spec = None
assert package_spec is None, package_spec

print(
    "INCOMPATIBLE_EXTENSION_REJECTED_OK "
    f"Blender {bpy.app.version_string} {PACKAGE}"
)
