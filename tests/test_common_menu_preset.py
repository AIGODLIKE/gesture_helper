from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PRESET_PATH = ROOT / "src" / "preset" / "Common Menu.json"
TRANSLATION_PATH = ROOT / "src" / "translate" / "zh_CN" / "preset.json"


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _element_values(element):
    yield element
    for child in element.get("element", {}).values():
        yield from _element_values(child)


class CommonMenuPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with PRESET_PATH.open(encoding="utf-8") as handle:
            cls.preset = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
        with TRANSLATION_PATH.open(encoding="utf-8") as handle:
            cls.translations = json.load(
                handle,
                object_pairs_hook=_reject_duplicate_keys,
            )

        cls.gesture = next(iter(cls.preset["gesture"].values()))
        cls.elements = [
            element
            for root in cls.gesture["element"].values()
            for element in _element_values(root)
        ]

    def test_side_button_menu_shortcut_is_enabled_in_common_3d_modes(self):
        self.assertTrue(self.gesture["enabled"])
        self.assertEqual(self.gesture["gesture_type"], "MENU")
        self.assertEqual(self.gesture["menu_style"], "COMPACT")
        self.assertTrue(self.gesture["menu_keep_open"])

        shortcut = json.loads(
            self.gesture["key_string"],
            object_pairs_hook=_reject_duplicate_keys,
        )
        self.assertEqual(shortcut["type"], "BUTTON4MOUSE")
        self.assertEqual(shortcut["value"], "PRESS")
        self.assertFalse(shortcut["any"])
        self.assertEqual(shortcut["key_modifier"], "NONE")
        self.assertFalse(shortcut["repeat"])
        for modifier in ("shift", "ctrl", "alt", "oskey"):
            self.assertFalse(shortcut[modifier])

        keymaps = json.loads(
            self.gesture["keymaps_string"],
            object_pairs_hook=_reject_duplicate_keys,
        )
        self.assertEqual(len(keymaps), len(set(keymaps)))
        self.assertEqual(keymaps[0], "3D View")
        self.assertGreaterEqual(
            set(keymaps),
            {
                "Object Mode",
                "Mesh",
                "Sculpt",
                "Pose",
                "Weight Paint",
                "Vertex Paint",
                "Grease Pencil",
                "Curves",
            },
        )

    def test_menu_is_context_aware_and_covers_practical_action_groups(self):
        root = next(iter(self.gesture["element"].values()))
        self.assertEqual(root["element_type"], "SELECTED_STRUCTURE")
        self.assertEqual(root["selected_type"], "IF")
        self.assertIn("VIEW_3D", root["poll_string"])

        names = {element["name"] for element in self.elements}
        self.assertGreaterEqual(
            names,
            {
                "Quick Access",
                "Mode Switch",
                "Viewport & Shading",
                "Object Tools",
                "Mesh Edit Tools",
                "Sculpt Tools",
                "Pose Tools",
                "Camera Settings",
                "Light Settings",
                "Mesh Object Settings",
                "Scene & Tool Values",
                "Unit Settings",
            },
        )

        polls = {
            element.get("poll_string", "")
            for element in self.elements
            if element.get("element_type") == "SELECTED_STRUCTURE"
        }
        self.assertTrue(any("C.mode == 'OBJECT'" in poll for poll in polls))
        self.assertTrue(any("C.mode == 'EDIT_MESH'" in poll for poll in polls))
        self.assertTrue(any("C.mode == 'SCULPT'" in poll for poll in polls))
        self.assertTrue(any("C.mode == 'POSE'" in poll for poll in polls))

    def test_operator_arguments_and_useful_property_paths_are_structural(self):
        operators = {
            element.get("operator_bl_idname")
            for element in self.elements
            if element.get("element_type") == "OPERATOR"
        }
        self.assertGreaterEqual(
            operators,
            {
                "object.mode_set",
                "object.transform_apply",
                "object.origin_set",
                "object.modifier_add",
                "mesh.select_non_manifold",
                "mesh.remove_doubles",
                "mesh.normals_make_consistent",
                "object.voxel_remesh",
                "pose.transforms_clear",
            },
        )

        for element in self.elements:
            properties = element.get("operator_properties")
            if properties is None:
                continue
            parsed = ast.literal_eval(properties)
            self.assertIsInstance(parsed, dict, element["name"])

        property_paths = {
            element.get("property_data_path")
            for element in self.elements
            if element.get("element_type") == "PROPERTY"
        }
        self.assertGreaterEqual(
            property_paths,
            {
                "space_data.lens",
                "space_data.clip_start",
                "space_data.clip_end",
                "space_data.shading.xray_alpha",
                "scene.render.resolution_percentage",
                "scene.render.fps",
                "scene.tool_settings.transform_pivot_point",
                "scene.tool_settings.use_snap",
                "scene.tool_settings.proportional_size",
                "scene.unit_settings.scale_length",
                "object.data.lens",
                "object.data.energy",
                "object.data.remesh_voxel_size",
            },
        )

    def test_every_custom_text_has_a_simplified_chinese_translation(self):
        texts = {
            PRESET_PATH.stem,
            self.preset["description"],
            self.gesture["name"],
            self.gesture["description"],
            *(element["name"] for element in self.elements),
        }
        missing = sorted(text for text in texts if text not in self.translations)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
