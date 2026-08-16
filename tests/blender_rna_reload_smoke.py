"""Verify PropertyGroup enums refresh when a Python module is reloaded."""

from __future__ import annotations

import sys
from pathlib import Path

import addon_utils
import bpy
from bpy.props import EnumProperty


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert addon_utils.enable("gesture_helper", default_set=True, persistent=False)

from gesture_helper.element import Element  # noqa: E402
from gesture_helper.utils.rna_register import (  # noqa: E402
    register_classes_safe,
    unregister_classes_safe,
)


element_types = {
    item.identifier
    for item in Element.bl_rna.properties["element_type"].enum_items
}
assert "SPLIT" in element_types, element_types


class GHReloadProbe(bpy.types.PropertyGroup):
    item_type: EnumProperty(items=(("OLD", "Old", ""),))


# Stale-class replacement only applies to this add-on's own classes; mark the
# probe as a previous gesture_helper build (a reloaded module keeps its name).
# Use a real module so register_class can resolve the stringized annotations.
_OWNED_MODULE = "gesture_helper.element.element_property"
GHReloadProbe.__module__ = _OWNED_MODULE

old_probe = GHReloadProbe
bpy.utils.register_class(old_probe)
assert {
    item.identifier
    for item in old_probe.bl_rna.properties["item_type"].enum_items
} == {"OLD"}


class GHReloadProbe(bpy.types.PropertyGroup):
    item_type: EnumProperty(
        items=(("OLD", "Old", ""), ("SPLIT", "Split", "")),
    )


GHReloadProbe.__module__ = _OWNED_MODULE

new_probe = GHReloadProbe
register_classes_safe((new_probe,))
assert new_probe.is_registered
assert bpy.types.PropertyGroup.bl_rna_get_subclass_py("GHReloadProbe") is new_probe
assert {
    item.identifier
    for item in new_probe.bl_rna.properties["item_type"].enum_items
} == {"OLD", "SPLIT"}
unregister_classes_safe((new_probe,))


# A same-named PropertyGroup owned by an unrelated add-on must never be
# unregistered by our safe-registration path.
class GHForeignProbe(bpy.types.PropertyGroup):
    item_type: EnumProperty(items=(("FOREIGN", "Foreign", ""),))


# Any real module without "gesture_helper" in its dotted path works here;
# it must also expose EnumProperty for the stringized annotation resolution.
GHForeignProbe.__module__ = "bpy.props"
foreign = GHForeignProbe
bpy.utils.register_class(foreign)


class GHForeignProbe(bpy.types.PropertyGroup):
    item_type: EnumProperty(items=(("REPLACEMENT", "Replacement", ""),))


GHForeignProbe.__module__ = _OWNED_MODULE
replacement = GHForeignProbe
try:
    register_classes_safe((replacement,))
except (RuntimeError, ValueError):
    # Blender may reject the duplicate identifier outright; the contract
    # under test is only that the foreign class stays registered.
    pass
assert foreign.is_registered, "foreign add-on class must survive"
if replacement.is_registered:
    unregister_classes_safe((replacement,))
bpy.utils.unregister_class(foreign)

addon_utils.disable("gesture_helper", default_set=True)
print(f"RNA_RELOAD_SMOKE_OK Blender {bpy.app.version_string}")
