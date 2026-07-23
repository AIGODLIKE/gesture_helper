from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "radial_collision.py"
SPEC = importlib.util.spec_from_file_location("radial_collision", MODULE_PATH)
collision = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(collision)


class RadialCollisionTests(unittest.TestCase):
    def assert_no_overlap(self, records, offsets, padding):
        resolved = [
            (key, collision.translate_rect(rect, offsets[key]))
            for key, rect, _direction in records
        ]
        for index, (key_a, rect_a) in enumerate(resolved):
            for key_b, rect_b in resolved[index + 1:]:
                self.assertFalse(
                    collision.rects_overlap(rect_a, rect_b, padding),
                    f"{key_a} overlaps {key_b}: {rect_a}, {rect_b}",
                )

    def test_adjacent_directions_move_outward_without_overlap(self):
        records = [
            ("1", (20.0, -15.0, 180.0, 15.0), (1.0, 0.0)),
            ("2", (15.0, 0.0, 175.0, 30.0), (1.0, 1.0)),
            ("3", (-80.0, 10.0, 80.0, 40.0), (0.0, 1.0)),
        ]
        offsets = collision.resolve_radial_collisions(records, padding=4.0)

        self.assertGreater(offsets["2"][0], 0.0)
        self.assertGreater(offsets["2"][1], 0.0)
        self.assertGreater(offsets["3"][1], 0.0)
        self.assert_no_overlap(records, offsets, 4.0)

    def test_direction_nine_moves_below_direction_seven(self):
        records = [
            ("7", (-60.0, -80.0, 60.0, -45.0), (0.0, -1.0)),
            ("9", (-100.0, -100.0, 100.0, -40.0), (0.0, -1.0)),
        ]
        offsets = collision.resolve_radial_collisions(records, padding=4.0)

        self.assertEqual(offsets["7"], (0.0, 0.0))
        self.assertLess(offsets["9"][1], 0.0)
        self.assert_no_overlap(records, offsets, 4.0)

    def test_viewport_clamp_is_deterministic_and_does_not_drift(self):
        records = [
            ("1", (170.0, -20.0, 250.0, 20.0), (1.0, 0.0)),
            ("2", (160.0, 0.0, 245.0, 40.0), (1.0, 1.0)),
        ]
        viewport = (-200.0, -100.0, 200.0, 100.0)

        first = collision.resolve_radial_collisions(
            records, viewport=viewport, padding=4.0,
        )
        second = collision.resolve_radial_collisions(
            records, viewport=viewport, padding=4.0,
        )

        self.assertEqual(first, second)
        self.assert_no_overlap(records, first, 4.0)
        for key, rect, _direction in records:
            moved = collision.translate_rect(rect, first[key])
            if moved[2] - moved[0] <= viewport[2] - viewport[0]:
                self.assertGreaterEqual(moved[0], viewport[0])
                self.assertLessEqual(moved[2], viewport[2])


if __name__ == "__main__":
    unittest.main()
