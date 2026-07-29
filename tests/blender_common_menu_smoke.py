"""Import the common side-button menu and validate live Blender contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import addon_utils
import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert addon_utils.enable("gesture_helper", default_set=True, persistent=False)

from gesture_helper.element.element_status import (  # noqa: E402
    get_operator_argument_error,
)
from gesture_helper.ops.export_import import Import  # noqa: E402
from gesture_helper.utils.gesture_items import (  # noqa: E402
    get_gesture_extension_items,
)
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public_cache import PublicCacheFunc  # noqa: E402


class FakeImport:
    def __init__(self, path):
        self.path = path
        self.reports = []

    def read_json(self):
        with open(self.path, encoding="utf-8") as handle:
            return json.load(handle)

    def report(self, level, message):
        self.reports.append((set(level), message))


def view3d_override():
    window = bpy.context.window
    assert window is not None
    area = next(item for item in window.screen.areas if item.type == "VIEW_3D")
    region = next(item for item in area.regions if item.type == "WINDOW")
    return {
        "window": window,
        "screen": window.screen,
        "area": area,
        "region": region,
    }


def set_active(obj):
    for selected in list(bpy.context.selected_objects):
        selected.select_set(False)
    if obj is not None:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def descendants(element):
    yield element
    for child in element.element:
        yield from descendants(child)


def named_element(gesture, name):
    matches = [element for element in gesture.element_iteration if element.name == name]
    assert len(matches) == 1, (name, [element.name for element in matches])
    return matches[0]


def visible_names(elements):
    return [item.name for item in get_gesture_extension_items(elements)]


def assert_editable_properties(element):
    properties = [item for item in descendants(element) if item.is_property_display]
    assert properties, element.name
    for item in properties:
        resolved = item.resolve_property()
        assert resolved is not None, (element.name, item.name, item.property_data_path)
        assert item.display_property_is_editable, (
            element.name,
            item.name,
            item.property_data_path,
            resolved[1].type,
        )


store = get_gesture_store()
assert store is not None
store.gesture.clear()

fake = FakeImport(REPOSITORY / "src" / "preset" / "Common Menu.json")
assert Import.gesture_import(fake), fake.reports
PublicCacheFunc.cache_clear()

assert len(store.gesture) == 1
gesture = store.gesture[0]
assert gesture.name == "Common Side Button Menu"
assert gesture.gesture_type == "MENU"
assert gesture.menu_style == "COMPACT"
assert gesture.menu_keep_open
assert gesture.key["type"] == "BUTTON4MOUSE"
assert gesture.key["value"] == "PRESS"

expected_keymaps = set(gesture.keymaps)
addon_config = bpy.context.window_manager.keyconfigs.addon
kmis = []
for keymap in addon_config.keymaps:
    for kmi in keymap.keymap_items:
        if (
            kmi.idname == "wm.gesture_menu"
            and getattr(kmi.properties, "gesture", "") == gesture.name
        ):
            kmis.append((keymap.name, kmi.type, kmi.value))
assert {item[0] for item in kmis} == expected_keymaps, kmis
assert all(item[1:] == ("BUTTON4MOUSE", "PRESS") for item in kmis), kmis

for element in gesture.element_iteration:
    if not element.is_operator:
        continue
    assert element.operator_func is not None, (
        element.name,
        element.operator_bl_idname,
    )
    assert get_operator_argument_error(element) is None, (
        element.name,
        element.operator_bl_idname,
        element.operator_properties,
    )

created_objects = []
created_data = []
with bpy.context.temp_override(**view3d_override()):
    cube = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
    set_active(cube)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    root_names = visible_names(gesture.element)
    assert {
        "Quick Access",
        "Mode Switch",
        "Viewport & Shading",
        "Object Tools",
        "Mesh Object Settings",
        "Scene & Tool Values",
    } <= set(root_names), root_names

    mode_switch = named_element(gesture, "Mode Switch")
    assert {
        "Object Mode",
        "Edit Mode",
        "Sculpt Mode",
        "Weight Paint",
        "Vertex Paint",
        "Texture Paint",
    } <= set(visible_names(mode_switch.element))

    for group_name in (
        "Viewport & Shading",
        "Object Tools",
        "Mesh Object Settings",
        "Scene & Tool Values",
    ):
        assert_editable_properties(named_element(gesture, group_name))

    bpy.ops.object.mode_set(mode="EDIT")
    edit_names = visible_names(gesture.element)
    assert "Mesh Edit Tools" in edit_names, edit_names
    assert "Object Tools" not in edit_names, edit_names
    assert_editable_properties(named_element(gesture, "Auto Merge Settings"))
    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.mode_set(mode="SCULPT")
    sculpt_names = visible_names(gesture.element)
    assert "Sculpt Tools" in sculpt_names, sculpt_names
    assert_editable_properties(named_element(gesture, "Sculpt Tools"))
    bpy.ops.object.mode_set(mode="OBJECT")

    camera_data = bpy.data.cameras.new("GestureCommonCamera")
    camera = bpy.data.objects.new("GestureCommonCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    created_objects.append(camera)
    created_data.append(camera_data)
    set_active(camera)
    camera_names = visible_names(gesture.element)
    assert "Camera Settings" in camera_names, camera_names
    assert_editable_properties(named_element(gesture, "Camera Settings"))

    light_data = bpy.data.lights.new("GestureCommonLight", "POINT")
    light = bpy.data.objects.new("GestureCommonLight", light_data)
    bpy.context.scene.collection.objects.link(light)
    created_objects.append(light)
    created_data.append(light_data)
    set_active(light)
    light_names = visible_names(gesture.element)
    assert "Light Settings" in light_names, light_names
    assert_editable_properties(named_element(gesture, "Light Settings"))

    empty = bpy.data.objects.new("GestureCommonEmpty", None)
    bpy.context.scene.collection.objects.link(empty)
    created_objects.append(empty)
    set_active(empty)
    empty_names = visible_names(gesture.element)
    assert "Empty Settings" in empty_names, empty_names
    assert_editable_properties(named_element(gesture, "Empty Settings"))

    armature_data = bpy.data.armatures.new("GestureCommonArmature")
    armature = bpy.data.objects.new("GestureCommonArmature", armature_data)
    bpy.context.scene.collection.objects.link(armature)
    created_objects.append(armature)
    created_data.append(armature_data)
    set_active(armature)
    bpy.ops.object.mode_set(mode="EDIT")
    armature_data.edit_bones.new("Bone")
    bpy.ops.object.mode_set(mode="POSE")
    pose_names = visible_names(gesture.element)
    assert "Pose Tools" in pose_names, pose_names
    bpy.ops.object.mode_set(mode="OBJECT")

    set_active(cube)
    for obj in created_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in created_data:
        if isinstance(data, bpy.types.Camera):
            bpy.data.cameras.remove(data)
        elif isinstance(data, bpy.types.Light):
            bpy.data.lights.remove(data)
        elif isinstance(data, bpy.types.Armature):
            bpy.data.armatures.remove(data)

addon_utils.disable("gesture_helper", default_set=True)
print(f"COMMON_MENU_SMOKE_OK Blender {bpy.app.version_string}: {len(kmis)} keymaps")
