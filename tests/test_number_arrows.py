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
        decrement, increment = number_arrows.number_arrow_rects(
            (10.0, 20.0, 110.0, 44.0),
            number_arrows.number_arrow_slot_width(24.0),
        )

        self.assertEqual(decrement, (10.0, 20.0, 27.28, 44.0))
        self.assertEqual(increment, (92.72, 20.0, 110.0, 44.0))
        self.assertEqual(number_arrows.number_arrow_direction((12.0, 32.0), decrement, increment), -1)
        self.assertEqual(number_arrows.number_arrow_direction((108.0, 32.0), decrement, increment), 1)
        self.assertEqual(number_arrows.number_arrow_direction((50.0, 32.0), decrement, increment), 0)

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
