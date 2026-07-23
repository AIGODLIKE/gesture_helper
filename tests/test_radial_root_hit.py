from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "element" / "extension_hit.py"
SPEC = importlib.util.spec_from_file_location("extension_hit", MODULE_PATH)
extension_hit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(extension_hit)


class FakeSession:
    def __init__(self):
        self.layout_token = object()


class FakeOps:
    def __init__(self):
        self.session = FakeSession()


class FakeElement:
    def __init__(self, direction, token, *, item_area=None, panel_area=None, layout=False):
        self.direction = str(direction)
        self._gesture_layout_token = token
        self.item_draw_area = item_area
        self.extension_draw_area = panel_area
        self.is_layout_container = layout


class RadialRootHitTests(unittest.TestCase):
    def setUp(self):
        self.ops = FakeOps()
        self.token = self.ops.session.layout_token

    def element(self, direction, *, item_area=None, panel_area=None, layout=False):
        return FakeElement(
            direction,
            self.token,
            item_area=item_area,
            panel_area=panel_area,
            layout=layout,
        )

    def test_visible_button_overrides_the_angular_direction(self):
        right = self.element(1, item_area=(90.0, 40.0, 150.0, 70.0))
        up = self.element(3, item_area=(-30.0, 90.0, 30.0, 120.0))

        hit = extension_hit.find_radial_root_hit(
            {"1": right, "3": up},
            self.ops,
            mouse=(100.0, 50.0),
            preferred_direction=3,
        )

        self.assertEqual(hit, ("1", right))

    def test_angle_item_wins_when_valid_hit_areas_overlap(self):
        area = (10.0, 10.0, 80.0, 50.0)
        right = self.element(1, item_area=area)
        diagonal = self.element(2, item_area=area)

        hit = extension_hit.find_radial_root_hit(
            {"1": right, "2": diagonal},
            self.ops,
            mouse=(20.0, 20.0),
            preferred_direction=2,
        )

        self.assertEqual(hit, ("2", diagonal))

    def test_layout_root_uses_its_panel_area(self):
        layout = self.element(
            4,
            item_area=(200.0, 200.0, 220.0, 220.0),
            panel_area=(-120.0, 20.0, -20.0, 100.0),
            layout=True,
        )

        hit = extension_hit.find_radial_root_hit(
            {"4": layout}, self.ops, mouse=(-40.0, 50.0),
        )

        self.assertEqual(hit, ("4", layout))

    def test_direction_nine_panel_hit_blocks_the_angle_selection(self):
        extension = self.element(
            9,
            item_area=(-10.0, -10.0, 10.0, 10.0),
            panel_area=(-80.0, -140.0, 80.0, -80.0),
        )

        hit = extension_hit.find_radial_root_hit(
            {"9": extension}, self.ops, mouse=(0.0, -100.0),
        )

        self.assertEqual(hit, ("9", extension))
        selection = extension_hit.resolve_radial_root_selection(
            7, self.element(7, item_area=(-20.0, -80.0, 20.0, -40.0)), hit,
        )
        self.assertEqual(selection, (None, None))

    def test_missing_or_malformed_hit_keeps_angle_selection(self):
        angular = self.element(3, item_area=(-20.0, 80.0, 20.0, 110.0))

        self.assertEqual(
            extension_hit.resolve_radial_root_selection(3, angular, None),
            (3, angular),
        )
        self.assertEqual(
            extension_hit.resolve_radial_root_selection(
                3, angular, ("invalid", self.element(1)),
            ),
            (3, angular),
        )

    def test_stale_or_missing_hit_areas_are_ignored(self):
        stale = FakeElement(
            1,
            object(),
            item_area=(0.0, 0.0, 100.0, 100.0),
        )
        undrawn = self.element(2)

        hit = extension_hit.find_radial_root_hit(
            {"1": stale, "2": undrawn}, self.ops, mouse=(20.0, 20.0),
        )

        self.assertIsNone(hit)


if __name__ == "__main__":
    unittest.main()
