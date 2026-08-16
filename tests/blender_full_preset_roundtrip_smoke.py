"""Round-trip the complete gesture library and execute a restored action."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import addon_utils
import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert addon_utils.enable("gesture_helper", default_set=True, persistent=False)

from gesture_helper.gesture.gesture_keymap import GestureKeymap  # noqa: E402
from gesture_helper.ops.gesture_cure import add_all_preset  # noqa: E402
from gesture_helper.utils.gesture_persistence import (  # noqa: E402
    cancel_scheduled_gesture_save,
    capture_gesture_snapshot,
    has_unsaved_gesture_changes,
)
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402
from gesture_helper.utils.public_cache import PublicCacheFunc  # noqa: E402
from gesture_helper.utils.strict_json import (  # noqa: E402
    load_json_strict,
    loads_json_strict,
)


ROUNDTRIP_ROOT = REPOSITORY / ".tmp" / f"full_preset_roundtrip_{os.getpid()}"
EXPORT_PATH = ROUNDTRIP_ROOT / "complete_gesture_library.json"
PROBE_NAME = "Full Preset Roundtrip Probe"
PROBE_OPERATOR = "wm.gesture_helper_roundtrip_probe"
PROBE_RESULT_KEY = "gesture_helper_roundtrip_probe_executed"


class WM_OT_GestureHelperRoundtripProbe(bpy.types.Operator):
    bl_idname = PROBE_OPERATOR
    bl_label = "Gesture Helper Roundtrip Probe"

    def execute(self, context):
        context.scene[PROBE_RESULT_KEY] = context.scene.get(PROBE_RESULT_KEY, 0) + 1
        return {"FINISHED"}


def normalize_json_data(value):
    return loads_json_strict(json.dumps(value, ensure_ascii=True))


def gesture_kmis():
    addon_config = bpy.context.window_manager.keyconfigs.addon
    assert addon_config is not None
    result = []
    for keymap in addon_config.keymaps:
        for kmi in keymap.keymap_items:
            if kmi.idname not in {"wm.gesture_operator", "wm.gesture_menu"}:
                continue
            result.append((
                keymap.name,
                kmi.idname,
                kmi.map_type,
                kmi.type,
                kmi.value,
                bool(kmi.any),
                int(kmi.shift),
                int(kmi.ctrl),
                int(kmi.alt),
                int(kmi.oskey),
                getattr(kmi, "key_modifier", "NONE"),
                getattr(kmi.properties, "gesture", ""),
            ))
    return sorted(result)


def clear_library(store):
    cancel_scheduled_gesture_save()
    PublicCacheFunc.prepare_store_replacement()
    store.gesture.clear()
    store.index_gesture = 0
    assert not GestureKeymap.key_restart()


success = False
bpy.utils.register_class(WM_OT_GestureHelperRoundtripProbe)
ROUNDTRIP_ROOT.mkdir(parents=True, exist_ok=True)
try:
    store = get_gesture_store()
    assert store is not None
    clear_library(store)

    preset_count = add_all_preset()
    assert preset_count > 0

    probe = store.gesture.add()
    probe.name = PROBE_NAME
    probe.gesture_type = "RADIAL"
    probe.enabled = True
    probe.selected = True
    probe.key_string = json.dumps({
        "type": "A",
        "value": "PRESS",
        "shift": True,
        "ctrl": True,
        "alt": True,
    })
    probe.keymaps_string = json.dumps(["Window"])

    action = probe.element.add()
    action.name = "Execute Roundtrip Probe"
    action.element_type = "OPERATOR"
    action.operator_type = "OPERATOR"
    action.operator_bl_idname = PROBE_OPERATOR
    action.operator_properties = "{}"
    action.operator_context = "EXEC_DEFAULT"
    action.direction = "1"

    for gesture in store.gesture:
        gesture.selected = True
    PublicCacheFunc.cache_clear()
    cancel_scheduled_gesture_save()
    assert not GestureKeymap.key_restart()

    before_data = normalize_json_data(get_pref().get_gesture_data(True))
    before_kmis = gesture_kmis()
    assert PROBE_NAME in {gesture[11] for gesture in before_kmis}

    export_result = bpy.ops.wm.gesture_export(
        "EXEC_DEFAULT",
        filepath=str(EXPORT_PATH),
        description="Complete gesture library roundtrip smoke",
    )
    assert export_result == {"FINISHED"}, export_result
    assert EXPORT_PATH.is_file()
    with EXPORT_PATH.open("r", encoding="utf-8") as handle:
        exported = load_json_strict(handle)
    assert exported["gesture"] == before_data

    clear_library(store)
    assert len(store.gesture) == 0
    assert not gesture_kmis()

    import_result = bpy.ops.wm.gesture_import(
        "EXEC_DEFAULT",
        filepath=str(EXPORT_PATH),
        run_execute=True,
    )
    assert import_result == {"FINISHED"}, import_result
    assert normalize_json_data(get_pref().get_gesture_data(True)) == before_data
    assert gesture_kmis() == before_kmis

    restored = next(
        gesture for gesture in store.gesture if gesture.name == PROBE_NAME
    )
    clean_snapshot = capture_gesture_snapshot()
    assert clean_snapshot is not None
    assert not has_unsaved_gesture_changes(clean_snapshot)
    restored.menu_keep_open = not restored.menu_keep_open
    assert has_unsaved_gesture_changes(capture_gesture_snapshot())
    restored.menu_keep_open = not restored.menu_keep_open
    assert not has_unsaved_gesture_changes(capture_gesture_snapshot())

    assert len(restored.element) == 1
    restored_action = restored.element[0]
    assert restored_action.operator_func is not None

    bpy.context.scene[PROBE_RESULT_KEY] = 0
    assert restored_action.running_operator() is None
    assert bpy.context.scene[PROBE_RESULT_KEY] == 1

    success = True
    print(
        "FULL_PRESET_ROUNDTRIP_SMOKE_OK "
        f"Blender {bpy.app.version_string} presets={preset_count} "
        f"gestures={len(store.gesture)} kmis={len(before_kmis)}"
    )
finally:
    cancel_scheduled_gesture_save()
    bpy.context.scene.pop(PROBE_RESULT_KEY, None)
    try:
        clear_library(get_gesture_store())
    except Exception:
        pass
    bpy.utils.unregister_class(WM_OT_GestureHelperRoundtripProbe)
    addon_utils.disable("gesture_helper", default_set=True)
    if success:
        EXPORT_PATH.unlink(missing_ok=True)
        try:
            ROUNDTRIP_ROOT.rmdir()
        except OSError:
            pass
