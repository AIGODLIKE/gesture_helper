from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "number_arrows.py"
SPEC = importlib.util.spec_from_file_location("_number_arrows_test", MODULE_PATH)
number_arrows = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(number_arrows)


class NumberArrowTests(unittest.TestCase):
    def test_numeric_field_uses_symmetric_edge_slots(self):
        decrement, value, increment = number_arrows.number_field_rects(
            (10.0, 20.0, 110.0, 44.0),
            number_arrows.number_arrow_slot_width(24.0),
        )

        self.assertEqual(decrement, (10.0, 20.0, 29.68, 44.0))
        self.assertEqual(value, (29.68, 20.0, 90.32, 44.0))
        self.assertEqual(increment, (90.32, 20.0, 110.0, 44.0))
        self.assertEqual(number_arrows.number_arrow_direction((12.0, 32.0), decrement, increment), -1)
        self.assertEqual(number_arrows.number_arrow_direction((108.0, 32.0), decrement, increment), 1)
        self.assertEqual(number_arrows.number_arrow_direction((50.0, 32.0), decrement, increment), 0)
        self.assertEqual(
            number_arrows.number_field_part((12.0, 32.0), decrement, value, increment),
            number_arrows.NUMBER_PART_DECREMENT,
        )
        self.assertEqual(
            number_arrows.number_field_part((50.0, 32.0), decrement, value, increment),
            number_arrows.NUMBER_PART_VALUE,
        )
        self.assertEqual(
            number_arrows.number_field_part((108.0, 32.0), decrement, value, increment),
            number_arrows.NUMBER_PART_INCREMENT,
        )

    def test_chevron_matches_native_row_proportions(self):
        slot = number_arrows.number_arrow_slot_width(24.0)
        half_width, half_height, line_width = number_arrows.number_arrow_chevron(
            24.0,
            slot,
        )

        self.assertAlmostEqual(half_width, 2.736, places=5)
        self.assertAlmostEqual(half_height, 4.56, places=5)
        self.assertAlmostEqual(line_width, 1.32, places=5)

    def test_part_corners_keep_only_the_exposed_field_corners(self):
        self.assertEqual(
            number_arrows.number_field_corner_masks(),
            (
                (True, False, False, True),
                (False, False, False, False),
                (False, True, True, False),
            ),
        )
        self.assertEqual(
            number_arrows.number_field_corner_masks((False, True, False, True)),
            (
                (False, False, False, True),
                (False, False, False, False),
                (False, True, False, False),
            ),
        )

    def test_arrow_slots_clamp_for_a_narrow_field(self):
        decrement, increment = number_arrows.number_arrow_rects(
            (0.0, 0.0, 10.0, 20.0),
            20.0,
        )

        self.assertEqual(decrement, (0.0, 0.0, 5.0, 20.0))
        self.assertEqual(increment, (5.0, 0.0, 10.0, 20.0))

    def test_global_preference_is_honored_and_missing_value_falls_back_on(self):
        context = type("Context", (), {
            "preferences": type("Preferences", (), {
                "view": type("View", (), {"show_number_arrows": False})(),
            })(),
        })()
        self.assertFalse(number_arrows.show_number_arrows(context))
        self.assertTrue(number_arrows.show_number_arrows(object()))


if __name__ == "__main__":
    unittest.main()
