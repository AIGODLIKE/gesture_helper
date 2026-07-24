from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "layout_scale.py"
SPEC = importlib.util.spec_from_file_location("layout_scale", MODULE_PATH)
layout_scale = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(layout_scale)


class FakeNode:
    def __init__(self, *, legacy=1.0, x=1.0, y=1.0, stored=()):
        self.layout_scale = legacy
        self.layout_scale_x = x
        self.layout_scale_y = y
        self._stored = set(stored)

    def is_property_set(self, name):
        return name in self._stored


class LayoutScaleTests(unittest.TestCase):
    def test_axes_are_clamped_independently(self):
        node = FakeNode(x=10.0, y=0.1, stored={"layout_scale_x", "layout_scale_y"})
        self.assertEqual(layout_scale.layout_scale_pair(node), (4.0, 0.25))

    def test_stored_legacy_scale_fills_unset_axes(self):
        node = FakeNode(legacy=1.5, x=1.0, y=0.75, stored={"layout_scale", "layout_scale_y"})
        self.assertEqual(layout_scale.layout_scale_pair(node), (1.5, 0.75))

    def test_missing_axis_attributes_fall_back_to_legacy_scale(self):
        node = type("LegacyNode", (), {"layout_scale": 1.25})()
        self.assertEqual(layout_scale.layout_scale_pair(node), (1.25, 1.25))

    def test_import_migration_is_recursive_and_preserves_explicit_axes(self):
        elements = {
            "0": {
                "element_type": "BOX",
                "layout_scale": 1.4,
                "layout_scale_x": 0.8,
                "element": {
                    "0": {
                        "element_type": "ROW",
                        "layout_scale": 1.2,
                    },
                },
            },
            "1": {
                "element_type": "OPERATOR",
                "layout_scale": 2.0,
            },
        }

        layout_scale.migrate_legacy_layout_scales(elements)

        self.assertEqual(elements["0"]["layout_scale_x"], 0.8)
        self.assertEqual(elements["0"]["layout_scale_y"], 1.4)
        nested = elements["0"]["element"]["0"]
        self.assertEqual(nested["layout_scale_x"], 1.2)
        self.assertEqual(nested["layout_scale_y"], 1.2)
        self.assertNotIn("layout_scale_x", elements["1"])


if __name__ == "__main__":
    unittest.main()
