"""Run with Blender to verify legacy preset assets import after upgrades.

Samples under ``tests/data/legacy_presets`` are real exports taken from
historical release tags:

- ``v104_maya_axis_coordinate.json``: oldest 1.x export shape (no icon data).
- ``v219_mx_preset_hyper.json``: v2.1.9 bundled preset whose ``key_string``
  carries the ``hyper``/``hyper_ui`` KMI fields that pre-2.2.0 exporters
  leaked on Blender 4.5+.
- ``v226_mesh_edge_with_script.json``: v2.2.6 export containing one legacy
  SCRIPT element that current versions must drop (with a user report) while
  keeping every other element.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import addon_utils
import bpy

REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

addon = addon_utils.enable("gesture_helper", default_set=True, persistent=False)
assert addon is not None

from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402

SAMPLES = Path(__file__).parent / "data" / "legacy_presets"


def count_elements(elements) -> int:
    total = 0
    for element in elements:
        total += 1
        total += count_elements(element.element)
    return total


def collect_operator_types(elements, found: set[str]) -> None:
    for element in elements:
        found.add(element.operator_type)
        collect_operator_types(element.element, found)


def import_sample(name: str):
    path = SAMPLES / name
    assert path.is_file(), f"missing sample {path}"
    store = get_gesture_store()
    assert store is not None
    store.gesture.clear()
    store.index_gesture = 0
    result = bpy.ops.wm.gesture_import(
        "EXEC_DEFAULT", filepath=str(path), run_execute=True
    )
    assert result == {'FINISHED'}, f"import failed for {name}: {result}"
    return store


# 1) Oldest 1.x preset shape imports completely.
store = import_sample("v104_maya_axis_coordinate.json")
assert len(store.gesture) == 1, len(store.gesture)
assert count_elements(store.gesture[0].element) == 28

# 2) A pre-2.2.0 export with leaked hyper KMI fields imports completely, and
# the stored shortcut is cleaned so re-exports stay schema-valid.
store = import_sample("v219_mx_preset_hyper.json")
assert len(store.gesture) == 3, len(store.gesture)
assert sum(count_elements(g.element) for g in store.gesture) == 78
for gesture in store.gesture:
    key_fields = set(json.loads(gesture.key_string))
    assert "hyper" not in key_fields, key_fields
    assert "hyper_ui" not in key_fields, key_fields

# 3) Legacy SCRIPT elements are dropped, everything else is preserved.
store = import_sample("v226_mesh_edge_with_script.json")
assert len(store.gesture) == 1, len(store.gesture)
assert count_elements(store.gesture[0].element) == 28  # 29 in file, 1 SCRIPT
operator_types: set[str] = set()
collect_operator_types(store.gesture[0].element, operator_types)
assert "SCRIPT" not in operator_types, operator_types

# 4) The persistence/legacy-preferences migration path shares the same
# sanitizer, so stored upgrade data with leaked hyper fields must also apply.
from gesture_helper.utils.gesture_persistence import _apply_gesture_data  # noqa: E402

legacy_payload = json.loads(
    (SAMPLES / "v219_mx_preset_hyper.json").read_text(encoding="utf-8")
)
_apply_gesture_data(store, legacy_payload["gesture"], target_index=0)
assert len(store.gesture) == 3, len(store.gesture)
for gesture in store.gesture:
    key_fields = set(json.loads(gesture.key_string))
    assert not (key_fields & {"hyper", "hyper_ui"}), key_fields

store.gesture.clear()
print("blender_legacy_preset_import_smoke: OK")
