"""Verify the Maya Grease Pencil mode actions on supported Blender versions."""

from __future__ import annotations

import sys
from pathlib import Path

import addon_utils
import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert addon_utils.enable("gesture_helper", default_set=True, persistent=False)

from gesture_helper.element.element_status import get_operator_argument_error  # noqa: E402
from gesture_helper.ops.export_import import Import  # noqa: E402
from gesture_helper.utils.expression import literal_to_dict  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.strict_json import load_json_strict  # noqa: E402


MODE_PAIRS = {
    "SCULPT_GREASE_PENCIL": "SCULPT_GPENCIL",
    "PAINT_GREASE_PENCIL": "PAINT_GPENCIL",
    "WEIGHT_GREASE_PENCIL": "WEIGHT_GPENCIL",
    "VERTEX_GREASE_PENCIL": "VERTEX_GPENCIL",
}


class FakeImport:
    def __init__(self, path):
        self.path = path
        self.reports = []

    def read_json(self):
        with open(self.path, encoding="utf-8") as handle:
            return load_json_strict(handle)

    def report(self, level, message):
        self.reports.append((set(level), message))


def view3d_override():
    window = bpy.context.window
    assert window is not None, "Grease Pencil smoke requires a window"
    area = next((item for item in window.screen.areas if item.type == "VIEW_3D"), None)
    assert area is not None, "Grease Pencil smoke requires a VIEW_3D area"
    region = next((item for item in area.regions if item.type == "WINDOW"), None)
    assert region is not None, "Grease Pencil smoke requires a window region"
    return {
        "window": window,
        "screen": window.screen,
        "area": area,
        "region": region,
    }


store = get_gesture_store()
assert store is not None
store.gesture.clear()

preset_path = REPOSITORY / "src" / "preset" / "Maya Switch Mode.json"
fake = FakeImport(preset_path)
assert Import.gesture_import(fake), fake.reports

gesture = next(
    item for item in store.gesture
    if item.name == "Maya Switch Mode"
)
mode_elements = {}
for element in gesture.element_iteration:
    if element.operator_bl_idname != "object.mode_set":
        continue
    stored = literal_to_dict(element.operator_properties)
    mode = stored.get("mode")
    if mode in MODE_PAIRS:
        mode_elements[mode] = element

assert set(mode_elements) == set(MODE_PAIRS), mode_elements

mode_prop = bpy.ops.object.mode_set.get_rna_type().properties["mode"]
available_modes = {item.identifier for item in mode_prop.enum_items}
expected_runtime_modes = {
    current: current if current in available_modes else legacy
    for current, legacy in MODE_PAIRS.items()
}
assert set(expected_runtime_modes.values()) <= available_modes, (
    available_modes,
    expected_runtime_modes,
)

for stored_mode, element in mode_elements.items():
    assert element.properties["mode"] == expected_runtime_modes[stored_mode], (
        stored_mode,
        element.properties,
        bpy.app.version_string,
    )
    assert get_operator_argument_error(element) is None, (
        element.name,
        element.operator_properties,
        element.properties,
    )
with bpy.context.temp_override(**view3d_override()):
    bpy.ops.object.select_all(action="DESELECT")
    # A populated primitive provides the layer/material state required by all
    # four paint/sculpt modes. Entering sculpt on an empty GP object can crash
    # Blender itself before Python receives an error.
    result = bpy.ops.object.grease_pencil_add(type="STROKE")
    assert result == {"FINISHED"}, result
    grease_pencil = bpy.context.object
    assert grease_pencil is not None
    assert grease_pencil.type in {"GPENCIL", "GREASEPENCIL"}, grease_pencil.type

    for stored_mode, element in mode_elements.items():
        if bpy.context.mode != "OBJECT":
            assert bpy.ops.object.mode_set(mode="OBJECT") == {"FINISHED"}
        element.operator_context = "EXEC_DEFAULT"
        error = element.running_operator()
        assert error is None, (stored_mode, error, element.properties)
        assert bpy.context.mode == stored_mode, (
            stored_mode,
            bpy.context.mode,
            element.properties,
        )

    if bpy.context.mode != "OBJECT":
        assert bpy.ops.object.mode_set(mode="OBJECT") == {"FINISHED"}

addon_utils.disable("gesture_helper", default_set=True)
print(
    f"GREASE_PENCIL_MODE_SMOKE_OK Blender {bpy.app.version_string}: "
    f"{sorted(expected_runtime_modes.values())}"
)
