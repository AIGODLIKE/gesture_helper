"""Import every bundled debug example into Blender and validate RNA values."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import addon_utils
import bpy
from bpy.app.translations import pgettext_tip


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert addon_utils.enable("gesture_helper", default_set=True, persistent=False)

from gesture_helper.ops.export_import import Import  # noqa: E402
from gesture_helper.utils.public_cache import PublicCacheFunc  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.preset import (  # noqa: E402
    DEBUG_ONLY_PRESET_NAMES,
    get_preset_gesture_list,
)
from gesture_helper.utils.public import get_pref  # noqa: E402
from gesture_helper.utils.selection import focus_element_settings  # noqa: E402
from gesture_helper.gesture.gesture_keymap import GestureKeymap  # noqa: E402
from gesture_helper.element.element_status import (  # noqa: E402
    ElementStatus,
    get_element_status,
    get_element_status_info,
    get_operator_argument_error,
)
from gesture_helper.gesture.gesture_input import get_runtime_action_element  # noqa: E402
from gesture_helper.gesture.gesture_session import ThresholdZone  # noqa: E402
from gesture_helper.utils.gesture_items import (  # noqa: E402
    get_gesture_direction_items,
    get_gesture_extension_items,
)


class FakeImport:
    def __init__(self, path):
        self.path = path
        self.reports = []

    def read_json(self):
        with open(self.path, encoding="utf-8") as handle:
            return json.load(handle)

    def report(self, level, message):
        self.reports.append((set(level), message))


store = get_gesture_store()
assert store is not None
store.gesture.clear()

presets = get_preset_gesture_list(include_debug_only=True)
example_names = sorted(name for name in presets if name.startswith("Example "))
assert example_names == sorted(DEBUG_ONLY_PRESET_NAMES), example_names

for name in example_names:
    fake = FakeImport(presets[name])
    assert Import.gesture_import(fake), (name, fake.reports)

# MX uses the same 3D-view Gizmo toggle as a normal bundled preset. Keep it
# as a PROPERTY element so its RNA path is resolved by the property runtime.
mx_preset = REPOSITORY / "src" / "preset" / "MX Preset.json"
mx_import = FakeImport(mx_preset)
assert Import.gesture_import(mx_import), mx_import.reports

# ``gesture_import`` is the low-level transactional loader. The real operator
# clears derived structure caches in ``execute`` after this method returns.
PublicCacheFunc.cache_clear()

assert {gesture.name for gesture in store.gesture} >= {
    "Radial Gesture Example",
    "Panel Menu Example",
    "Compact Menu Example",
    "Borderless Menu Example",
    "Element and Layout Example",
    "Modal Modes Example",
    "Direction Slots Example",
    "Operator Contexts Example",
    "Property Actions Example",
    "Practical Viewport Menu",
    "Validation States Example",
}

# Disabled examples must not create active shortcuts while still being fully
# represented in RNA.
assert not GestureKeymap.key_restart(), "disabled examples should not register KMIs"

modal_events = []
for gesture in store.gesture:
    for element in gesture.element_iteration:
        if element.is_operator and element.operator_type == "MODAL":
            modal_events.extend(element.modal_events)

number_modes = {
    event.number_value_mode
    for event in modal_events
    if event.control_property_type in {"INT", "FLOAT"}
}
bool_modes = {
    event.bool_value_mode
    for event in modal_events
    if event.control_property_type == "BOOLEAN"
}
enum_modes = {
    event.enum_value_mode
    for event in modal_events
    if event.control_property_type == "ENUM"
}
event_diagnostics = [
    (
        event.parent_element.name,
        event.control_property,
        event.control_property_type,
        event.number_value_mode,
        event.bool_value_mode,
        event.enum_value_mode,
    )
    for event in modal_events
]

assert number_modes >= {
    "ADD",
    "SUBTRACT",
    "SET_VALUE",
    "MOUSE_CHANGES_HORIZONTAL",
    "MOUSE_CHANGES_VERTICAL",
    "MOUSE_CHANGES_ARBITRARY",
}, event_diagnostics
assert bool_modes >= {
    "SET_TRUE",
    "SET_FALSE",
    "SWITCH",
}, event_diagnostics
assert enum_modes >= {
    "SET",
    "CYCLE",
    "TOGGLE",
}, event_diagnostics

cycle_options = {
    (event.enum_reverse, event.enum_wrap)
    for event in modal_events
    if event.enum_value_mode == "CYCLE"
}
assert cycle_options >= {
    (False, True),
    (True, True),
    (False, False),
    (True, False),
}, event_diagnostics
assert any(event.event_ctrl for event in modal_events), event_diagnostics
assert any(event.event_alt for event in modal_events), event_diagnostics
assert any(event.event_shift for event in modal_events), event_diagnostics


def _view3d_override():
    window = bpy.context.window
    assert window is not None, "Blender smoke requires a window context"
    area = next((item for item in window.screen.areas if item.type == "VIEW_3D"), None)
    assert area is not None, "Blender smoke requires a VIEW_3D area"
    region = next((item for item in area.regions if item.type == "WINDOW"), None)
    assert region is not None, "Blender smoke requires a VIEW_3D window region"
    return {
        "window": window,
        "screen": window.screen,
        "area": area,
        "region": region,
    }


def _all_elements(gesture):
    # ``gesture.element_iteration`` is already the cached recursive walk.
    yield from gesture.element_iteration


with bpy.context.temp_override(**_view3d_override()):
    gestures_by_name = {gesture.name: gesture for gesture in store.gesture}

    mx_gizmo_elements = [
        element
        for gesture in store.gesture
        for element in _all_elements(gesture)
        if (
            element.parent_gesture.name == "View"
            and element.name == "Show Gizmo"
            and element.property_data_path == "space_data.show_gizmo"
        )
    ]
    assert len(mx_gizmo_elements) == 1, mx_gizmo_elements
    mx_gizmo = mx_gizmo_elements[0]
    assert mx_gizmo.is_property_display
    assert mx_gizmo.resolve_property() is not None

    # Validate every non-fixture operator against the real Blender RNA. This
    # catches stale operator ids and malformed context_* arguments in examples.
    for gesture in store.gesture:
        if gesture.name == "Validation States Example":
            continue
        for element in _all_elements(gesture):
            if element.is_operator:
                assert element.operator_func is not None, (
                    gesture.name,
                    element.name,
                    element.operator_bl_idname,
                )
                assert get_operator_argument_error(element) is None, (
                    gesture.name,
                    element.name,
                    element.operator_bl_idname,
                    element.operator_properties,
                )

    # Property display examples must exercise every editable scalar RNA type.
    editable_property_types = set()
    for gesture in store.gesture:
        for element in _all_elements(gesture):
            if not element.is_property_display:
                continue
            resolved = element.resolve_property()
            if resolved is not None and element.display_property_is_editable:
                editable_property_types.add(resolved[1].type)
    assert editable_property_types >= {"BOOLEAN", "INT", "FLOAT", "ENUM"}, editable_property_types

    # Runtime help must come from Blender's native operator/property RNA. It is
    # presentation-only: Element RNA must not acquire an editable description.
    action_elements = [
        element
        for gesture in store.gesture
        for element in _all_elements(gesture)
        if element.is_operator or element.is_property_display
    ]
    assert action_elements
    assert all("description" not in element.bl_rna.properties for element in action_elements)

    source_counts = {"OPERATOR": 0, "PROPERTY": 0}
    missing_sources = []
    for element in action_elements:
        source = None
        if element.is_operator and element.operator_func is not None:
            source = element.operator_func.get_rna_type()
        elif element.is_property_display:
            resolved = element.resolve_property()
            if resolved is not None:
                source = resolved[1]

        native_description = ""
        if source is not None:
            description = source.description or ""
            if description:
                native_description = pgettext_tip(
                    description,
                    source.translation_context,
                )
                source_counts[element.element_type] += 1
        assert element.source_description == native_description, (
            element.name,
            element.source_description,
            native_description,
        )

        info = get_element_status_info(element, include_poll=True)
        expected_runtime = native_description if info.is_valid else info.message
        assert element.runtime_annotation_text == expected_runtime, (
            element.name,
            info.status,
            element.runtime_annotation_text,
            expected_runtime,
        )
        if source is not None and not native_description:
            missing_sources.append((element.name, element.element_type))

    assert source_counts["OPERATOR"] > 0, source_counts
    assert source_counts["PROPERTY"] > 0, source_counts
    assert not missing_sources, missing_sources

    # A layout direction describes the operator/property it will really run,
    # including nested layouts and explicit main-item selection.
    layouts_checked = 0
    fake_ops = SimpleNamespace()
    for gesture in store.gesture:
        for layout in _all_elements(gesture):
            if not layout.is_layout_container or layout.main_element is None:
                continue
            fake_session = SimpleNamespace(
                extension_hover=[],
                snapshot=SimpleNamespace(
                    direction_element=layout,
                    threshold_zone=ThresholdZone.BEYOND,
                ),
            )
            assert get_runtime_action_element(fake_session, fake_ops) == layout.main_element
            layouts_checked += 1
    assert layouts_checked > 0

    # The validation fixture intentionally contains unsupported shapes and
    # malformed entries so every status badge has a real RNA example.
    validation = gestures_by_name["Validation States Example"]
    validation_by_name = {
        element.name: element for element in _all_elements(validation)
    }
    expected_statuses = {
        "Valid Operator": ElementStatus.VALID,
        "Disabled Element": ElementStatus.DISABLED,
        "Missing Operator": ElementStatus.INVALID_OPERATOR,
        "Invalid Operator Arguments": ElementStatus.INVALID_ARGUMENTS,
        "Missing Property Path": ElementStatus.INVALID_PROPERTY,
        "String Display (Read Only)": ElementStatus.READ_ONLY_PROPERTY,
        "Array Display (Read Only)": ElementStatus.READ_ONLY_PROPERTY,
        "RNA Read-Only Enum": ElementStatus.READ_ONLY_PROPERTY,
        "Multi-Select Enum (Read Only)": ElementStatus.READ_ONLY_PROPERTY,
        "Orphan ELIF": ElementStatus.INVALID_STRUCTURE,
        "Invalid Condition Expression": ElementStatus.INVALID_STRUCTURE,
    }
    for name, expected in expected_statuses.items():
        actual = get_element_status(validation_by_name[name], include_poll=False)
        assert actual is expected, (name, actual, expected)
    assert (
        get_element_status(
            validation_by_name["Context-Dependent Operator"],
            include_poll=True,
        )
        is ElementStatus.POLL_BLOCKED
    )

    # The runtime repair click closes its overlay before calling this helper.
    # Verify the Blender-backed selection handoff reaches the existing editor
    # state without introducing a separate repair UI.
    broken = validation_by_name["Missing Operator"]
    draw = get_pref().draw_property
    assert tuple(broken.background_color) == tuple(draw.status_error_color)
    assert tuple(broken.extension_background_color) == tuple(draw.status_error_color)
    assert tuple(broken.text_color) == tuple(draw.text_active_color)
    assert focus_element_settings(broken)
    assert store.gesture[store.index_gesture].as_pointer() == validation.as_pointer()
    assert get_pref().active_element.as_pointer() == broken.as_pointer()
    assert get_pref().show_page == "GESTURE"

    # The direction example uses the special root child slot, not a layout
    # child whose direction is ignored by the radial dispatcher.
    directions = gestures_by_name["Direction Slots Example"]
    direction_map = get_gesture_direction_items(directions.element)
    assert set(direction_map) == {"1", "2", "3", "4", "5", "6", "7", "8", "9"}, direction_map
    assert direction_map["9"].is_child_gesture

    # Exercise the mutually exclusive IF / ELIF / ELSE example in all three
    # contexts. This prevents an overly broad IF from making ELIF unreachable.
    conditional = gestures_by_name["Element and Layout Example"]
    panel_menu = gestures_by_name["Panel Menu Example"]
    practical_menu = gestures_by_name["Practical Viewport Menu"]

    def visible_conditional_names():
        return {
            element.name
            for element in get_gesture_direction_items(conditional.element).values()
        }

    def visible_panel_names():
        return [
            element.name
            for element in get_gesture_extension_items(panel_menu.element)
        ]

    def visible_practical_names():
        return [
            element.name
            for element in get_gesture_extension_items(practical_menu.element)
        ]

    view_layer = bpy.context.view_layer
    original_active = view_layer.objects.active
    original_selected = list(bpy.context.selected_objects)
    assert original_active is not None and original_active.type == "MESH"
    assert visible_conditional_names() == {
        "Shade Smooth",
        "Wireframe",
        "Layout Containers",
    }
    assert visible_panel_names() == [
        "Frame Selected",
        "Show Overlays",
        "Dividing_Line",
        "Viewport Actions",
    ]
    assert visible_practical_names() == [
        "Frame Selected",
        "Dividing_Line",
        "View Actions",
        "Viewport Display",
        "Dividing_Line",
        "Selection",
        "Transform",
        "Object Display",
        "Mesh Shading",
    ]

    curve_data = bpy.data.curves.new("GestureExampleCurve", "CURVE")
    curve_object = bpy.data.objects.new("GestureExampleCurve", curve_data)
    bpy.context.scene.collection.objects.link(curve_object)
    try:
        for selected in original_selected:
            selected.select_set(False)
        curve_object.select_set(True)
        view_layer.objects.active = curve_object
        assert visible_conditional_names() == {
            "Show Name",
            "Curve Display",
            "Layout Containers",
        }
        assert visible_practical_names() == [
            "Frame Selected",
            "Dividing_Line",
            "View Actions",
            "Viewport Display",
            "Dividing_Line",
            "Selection",
            "Transform",
            "Object Display",
        ]

        curve_object.select_set(False)
        view_layer.objects.active = None
        assert visible_conditional_names() == {
            "View All",
            "Layout Containers",
        }
        assert visible_panel_names() == [
            "View All",
            "Dividing_Line",
            "Viewport Actions",
        ]
        assert visible_practical_names() == [
            "View All",
            "Dividing_Line",
            "View Actions",
            "Viewport Display",
            "Dividing_Line",
        ]
    finally:
        bpy.data.objects.remove(curve_object, do_unlink=True)
        bpy.data.curves.remove(curve_data)
        for selected in original_selected:
            selected.select_set(True)
        view_layer.objects.active = original_active

addon_utils.disable("gesture_helper", default_set=True)
print(f"EXAMPLE_PRESETS_SMOKE_OK Blender {bpy.app.version_string}: {len(example_names)} presets")
