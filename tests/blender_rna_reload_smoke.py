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


new_probe = GHReloadProbe
register_classes_safe((new_probe,))
assert new_probe.is_registered
assert bpy.types.PropertyGroup.bl_rna_get_subclass_py("GHReloadProbe") is new_probe
assert {
    item.identifier
    for item in new_probe.bl_rna.properties["item_type"].enum_items
} == {"OLD", "SPLIT"}
unregister_classes_safe((new_probe,))

addon_utils.disable("gesture_helper", default_set=True)
print(f"RNA_RELOAD_SMOKE_OK Blender {bpy.app.version_string}")
