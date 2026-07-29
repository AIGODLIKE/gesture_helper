"""Run with Blender to verify strict import rollback and lenient startup keymaps."""

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

from gesture_helper.gesture.gesture_keymap import GestureKeymap  # noqa: E402
from gesture_helper.ops.gesture_cure import (  # noqa: E402
    add_all_preset,
    get_all_preset_gesture_data,
)
from gesture_helper.ops.export_import import Import  # noqa: E402
from gesture_helper.utils.cache_state import CacheState  # noqa: E402
from gesture_helper.utils.gesture_persistence import _apply_gesture_data  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402
from gesture_helper.utils.public_cache import PublicCache, PublicCacheFunc  # noqa: E402
from gesture_helper.utils.selection import resolve_active_element  # noqa: E402
from gesture_helper.utils import property as property_utils  # noqa: E402
from gesture_helper.utils import selection as selection_utils  # noqa: E402
from gesture_helper.utils import ui_draw_sync  # noqa: E402


GESTURE_IDS = {"wm.gesture_operator", "wm.gesture_menu"}


def gesture_kmis():
    addon_config = bpy.context.window_manager.keyconfigs.addon
    result = []
    for keymap in addon_config.keymaps:
        for kmi in keymap.keymap_items:
            if kmi.idname not in GESTURE_IDS:
                continue
            result.append((
                keymap.name,
                kmi.idname,
                kmi.type,
                kmi.value,
                getattr(kmi.properties, "gesture", ""),
            ))
    return sorted(result)


def make_import(payload):
    reports = []
    fake = type("FakeImport", (), {})()
    fake.read_json = lambda: payload
    fake.report = lambda level, message: reports.append((set(level), message))
    return fake, reports


store = get_gesture_store()
assert store is not None
store.gesture.clear()

existing = store.gesture.add()
existing.name = "Existing"
existing.gesture_type = "RADIAL"
existing.key_string = json.dumps({"type": "RIGHTMOUSE", "value": "PRESS"})
existing.keymaps_string = json.dumps(["Window"])
store.index_gesture = 0
assert GestureKeymap.key_restart() == ()

before_data = get_pref().get_gesture_data(True)
before_kmis = gesture_kmis()
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert before_kmis, "Expected the original gesture shortcut to be registered"

# The real Ctrl+Alt+Shift bulk path must validate every bundled preset in one
# transaction while preserving the existing prefix and display grouping.
expected_gestures, preset_count = get_all_preset_gesture_data()
expected_names = [gesture["name"] for gesture in expected_gestures.values()]
assert add_all_preset() == preset_count
assert [gesture.name for gesture in store.gesture] == ["Existing", *expected_names]
_apply_gesture_data(store, before_data)
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis

# Snapshot/disk replacement is also transactional. Inject a post-assignment
# failure and verify the old live collection, index, cache, and KMIs return.
temporary_restore = dict(next(iter(before_data.values())))
temporary_restore["name"] = "Temporary Restore"
original_set_prop = property_utils.__set_prop__
injected = False


def fail_once_after_store_assignment(prop, path, value):
    global injected
    result = original_set_prop(prop, path, value)
    if prop == store and path == "gesture" and not injected:
        injected = True
        raise RuntimeError("injected restore failure")
    return result


property_utils.__set_prop__ = fail_once_after_store_assignment
try:
    try:
        _apply_gesture_data(store, {"0": temporary_restore})
    except RuntimeError as exc:
        assert "injected restore failure" in str(exc)
    else:
        raise AssertionError("Injected restore failure did not propagate")
finally:
    property_utils.__set_prop__ = original_set_prop

assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert store.index_gesture == 0
assert gesture_kmis() == before_kmis
assert not CacheState._pending_structure
assert not CacheState._dirty_gestures

duplicate_import = dict(next(iter(before_data.values())))
duplicate_import["name"] = "Existing"
fake, reports = make_import({"gesture": {"0": duplicate_import}})
assert Import.gesture_import(fake) is True
assert [gesture.name for gesture in store.gesture] == ["Existing", "Existing.001"]
assert any(item[-1] == "Existing.001" for item in gesture_kmis())
_apply_gesture_data(store, before_data)
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis

bad_gesture = dict(next(iter(before_data.values())))
bad_gesture["name"] = "Imported Bad"
bad_gesture["gesture_type"] = "MENU"
bad_gesture["menu_style"] = "COMPACT"
bad_gesture["key_string"] = json.dumps({
    "type": "NOT_A_REAL_EVENT",
    "value": "PRESS",
})
fake, reports = make_import({"gesture": {"0": bad_gesture}})

assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert store.index_gesture == 0
assert gesture_kmis() == before_kmis
assert reports and "Invalid imported shortcut" in reports[-1][1]
assert not CacheState._pending_structure
assert not CacheState._lock_deferred
assert not CacheState._dirty_gestures
PublicCacheFunc.ensure_gesture_structure(store.gesture[0])
assert store.gesture[0] in PublicCache.__gesture_element_iteration__

bad_shape = dict(bad_gesture)
bad_shape["key_string"] = "[]"
fake, reports = make_import({"gesture": {"0": bad_shape}})
assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis
assert reports and "expected an object" in reports[-1][1]

bad_layout = dict(next(iter(before_data.values())))
bad_layout["name"] = "Imported Bad Layout"
bad_layout["element"] = {
    "0": {
        "name": "Bad Row",
        "element_type": "ROW",
        "layout_alignment": "SIDEWAYS",
    },
}
fake, reports = make_import({"gesture": {"0": bad_layout}})
assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis
assert reports and "Invalid enum value" in reports[-1][1]

bad_modal = dict(next(iter(before_data.values())))
bad_modal["name"] = "Imported Bad Modal"
bad_modal["element"] = {
    "0": {
        "name": "Bad Modal",
        "element_type": "OPERATOR",
        "operator_type": "MODAL",
        "operator_bl_idname": "mesh.primitive_cube_add",
        "modal_events": {
            "0": {"event_type": "NOT_A_REAL_EVENT"},
        },
    },
}
fake, reports = make_import({"gesture": {"0": bad_modal}})
assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis
assert reports and "Invalid enum value" in reports[-1][1]

bad_id_property = dict(bad_gesture)
bad_id_property["key_string"] = json.dumps({
    "type": [1, "A"],
    "value": "PRESS",
})
fake, reports = make_import({"gesture": {"0": bad_id_property}})
assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis

disabled_bad = dict(bad_gesture)
disabled_bad["enabled"] = False
fake, reports = make_import({"gesture": {"0": disabled_bad}})
assert Import.gesture_import(fake) is False
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert gesture_kmis() == before_kmis

# Full-store replacement applies the same strict shortcut validation and must
# restore the previous collection, active index, and owned KMIs on failure.
try:
    _apply_gesture_data(
        store,
        {"0": disabled_bad},
        target_index=0,
        strict=True,
    )
except ValueError as exc:
    assert "Invalid imported shortcut" in str(exc)
else:
    raise AssertionError("Strict replacement accepted an invalid shortcut")
assert [gesture.name for gesture in store.gesture] == ["Existing"]
assert store.index_gesture == 0
assert gesture_kmis() == before_kmis

# A bad shortcut retained from lenient startup must not block a valid import.
existing = store.gesture[0]
existing.key_string = bad_gesture["key_string"]
old_failures = GestureKeymap.key_restart()
assert old_failures and old_failures[0].gesture_index == 0
good_import = dict(next(iter(before_data.values())))
good_import["name"] = "Imported Good"
fake, reports = make_import({"gesture": {"0": good_import}})
assert Import.gesture_import(fake) is True
assert [gesture.name for gesture in store.gesture] == ["Existing", "Imported Good"]
assert any(item[-1] == "Imported Good" for item in gesture_kmis())

# Restore the clean baseline before checking startup's lenient behavior.
_apply_gesture_data(store, before_data)
assert gesture_kmis() == before_kmis

# Disk/startup restore is intentionally lenient: preserve both gestures, keep
# every valid shortcut, and skip only the binding Blender cannot construct.
good_gesture = dict(next(iter(before_data.values())))
good_gesture["name"] = "Restored Good"
bad_gesture["name"] = "Restored Bad"
_apply_gesture_data(store, {"0": good_gesture, "1": bad_gesture})

assert [gesture.name for gesture in store.gesture] == ["Restored Good", "Restored Bad"]
restored_kmis = gesture_kmis()
assert any(item[-1] == "Restored Good" for item in restored_kmis)
assert not any(item[-1] == "Restored Bad" for item in restored_kmis)

# Reproduce the live-panel state that previously left invalid RNA proxies in
# relationship and selection caches during a complete CollectionProperty clear.
cache_source = store.gesture[0]
layout = cache_source.element.add()
layout.name = "Cached Layout"
layout.element_type = "BOX"
main_action = layout.element.add()
main_action.name = "Cached Main Action"
main_action.element_type = "OPERATOR"
main_action.operator_bl_idname = "view3d.view_all"
main_action.main_item = True
main_action.radio = True
PublicCacheFunc.cache_clear()
assert main_action.parent_element == layout
assert resolve_active_element(cache_source) == main_action
ui_draw_sync.set_frozen_ui_selection(cache_source, main_action)
assert ui_draw_sync._frozen_ui_selection

old_cache_proxies = (
    tuple(PublicCache.__element_prev_cache__.keys())
    + tuple(PublicCache.__element_prev_cache__.values())
    + tuple(PublicCache.__element_child_iteration__.keys())
    + tuple(
        item
        for children in PublicCache.__element_child_iteration__.values()
        for item in children
    )
    + tuple(PublicCache.__element_parent_element_cache__.keys())
    + tuple(PublicCache.__element_parent_element_cache__.values())
    + tuple(PublicCache.__element_parent_gesture_cache__.keys())
    + tuple(PublicCache.__element_parent_gesture_cache__.values())
    + tuple(PublicCache.__gesture_element_iteration__.keys())
    + tuple(
        item
        for children in PublicCache.__gesture_element_iteration__.values()
        for item in children
    )
    + tuple(selection_utils._ACTIVE_ELEMENT_CACHE.values())
)
old_cache_proxy_ids = {
    id(proxy) for proxy in old_cache_proxies
    if proxy is not None and hasattr(proxy, "as_pointer")
}

# Ctrl+Alt+Shift on the bundled-preset import button must bypass the picker,
# remove the previous collection, and install every bundled preset in the same
# stable grouping used by the add button's bulk-import path.
event = type("Event", (), {"ctrl": True, "alt": True, "shift": True})()
assert Import._replace_all_requested(True, event)
assert not Import._replace_all_requested(False, event)

assert preset_count > 0
result = bpy.ops.wm.gesture_import(
    run_execute=True,
    replace_with_all_presets=True,
)
assert result == {"FINISHED"}, result
assert [gesture.name for gesture in store.gesture] == expected_names
assert "Restored Good" not in expected_names
assert "Restored Bad" not in expected_names
assert store.index_gesture == 0
assert not ui_draw_sync._frozen_ui_selection
new_cache_proxies = (
    tuple(PublicCache.__element_prev_cache__.keys())
    + tuple(PublicCache.__element_prev_cache__.values())
    + tuple(PublicCache.__element_child_iteration__.keys())
    + tuple(PublicCache.__element_parent_element_cache__.keys())
    + tuple(PublicCache.__element_parent_element_cache__.values())
    + tuple(PublicCache.__element_parent_gesture_cache__.keys())
    + tuple(PublicCache.__element_parent_gesture_cache__.values())
    + tuple(PublicCache.__gesture_element_iteration__.keys())
    + tuple(selection_utils._ACTIVE_ELEMENT_CACHE.values())
)
assert not old_cache_proxy_ids.intersection(
    id(proxy)
    for proxy in new_cache_proxies
    if proxy is not None and hasattr(proxy, "as_pointer")
)

addon_utils.disable("gesture_helper", default_set=True)
print(f"IMPORT_KEYMAP_SMOKE_OK Blender {bpy.app.version_string}")
