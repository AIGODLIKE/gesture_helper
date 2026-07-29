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

    def test_slider_fill_stays_inside_the_middle_value_region(self):
        _decrement, value, _increment = number_arrows.number_field_rects(
            (10.0, 20.0, 110.0, 44.0),
            number_arrows.number_arrow_slot_width(24.0),
        )

        fill = number_arrows.number_slider_fill_rect(value, 0.25)

        self.assertEqual(fill[:2], value[:2])
        self.assertAlmostEqual(fill[2], 44.84)
        self.assertEqual(fill[3], value[3])
        self.assertGreaterEqual(fill[0], value[0])
        self.assertLessEqual(fill[2], value[2])
        self.assertEqual(
            number_arrows.number_slider_fill_rect(value, 1.0),
            value,
        )
        self.assertIsNone(number_arrows.number_slider_fill_rect(value, 0.0))

    def test_drag_uses_soft_range_without_leaping_across_large_ranges(self):
        value = number_arrows.number_drag_value(
            10.0,
            1.0,
            property_type='FLOAT',
            rna_step=10.0,
            hard_min=-3.402823466e38,
            hard_max=3.402823466e38,
            soft_min=0.0,
            soft_max=1_000_000.0,
        )

        self.assertEqual(value, 10.1)
        self.assertEqual(
            number_arrows.number_drag_value(
                10.0,
                1.0,
                property_type='FLOAT',
                rna_step=10.0,
                hard_min=-3.402823466e38,
                hard_max=3.402823466e38,
                soft_min=0.0,
                soft_max=1_000_000.0,
                precise=True,
            ),
            10.01,
        )

    def test_drag_clamps_to_soft_then_hard_limits(self):
        kwargs = dict(
            property_type='FLOAT',
            rna_step=100.0,
            hard_min=0.0,
            hard_max=10.0,
            soft_min=2.0,
            soft_max=8.0,
        )
        self.assertEqual(number_arrows.number_drag_value(5.0, 1000.0, **kwargs), 8.0)
        self.assertEqual(number_arrows.number_drag_value(5.0, -1000.0, **kwargs), 2.0)
        self.assertEqual(number_arrows.number_drag_value(9.0, 1000.0, **kwargs), 10.0)

    def test_drag_reports_clamped_delta_for_native_anchor_rebase(self):
        value, applied_delta = number_arrows.number_drag_value(
            5.0,
            1000.0,
            property_type='FLOAT',
            rna_step=100.0,
            hard_min=0.0,
            hard_max=10.0,
            soft_min=2.0,
            soft_max=8.0,
            return_applied_delta=True,
        )

        self.assertEqual(value, 8.0)
        self.assertEqual(applied_delta, 3.0)

    def test_drag_starting_outside_soft_range_does_not_snap_back(self):
        value = number_arrows.number_drag_value(
            200,
            -3.0,
            property_type='INT',
            rna_step=10.0,
            hard_min=1,
            hard_max=32767,
            soft_min=1,
            soft_max=100,
        )

        self.assertEqual(value, 198)

    def test_integer_drag_uses_blenders_soft_range_pixel_bands(self):
        common = dict(
            property_type='INT',
            rna_step=10,
            hard_min=-32768,
            hard_max=32767,
        )
        self.assertEqual(
            number_arrows.number_drag_value(
                500, 1, soft_min=0, soft_max=1000, **common,
            ),
            501,
        )
        self.assertEqual(
            number_arrows.number_drag_value(
                50, 2, soft_min=0, soft_max=100, **common,
            ),
            51,
        )
        self.assertEqual(
            number_arrows.number_drag_value(
                10, 16, soft_min=0, soft_max=20, **common,
            ),
            11,
        )

    def test_drag_expands_soft_range_to_native_one_two_five_boundaries(self):
        value = number_arrows.number_drag_value(
            250.0,
            1000.0,
            property_type='FLOAT',
            rna_step=100.0,
            hard_min=0.0,
            hard_max=1000.0,
            soft_min=0.0,
            soft_max=100.0,
        )

        self.assertEqual(value, 500.0)

    def test_wheel_step_uses_soft_and_hard_interaction_limits(self):
        kwargs = dict(
            property_type='FLOAT',
            configured_step=1.0,
            hard_min=-3.402823466e38,
            hard_max=3.402823466e38,
            soft_min=0.0,
            soft_max=1_000_000.0,
        )
        self.assertEqual(number_arrows.number_step_value(0.0, -1, **kwargs), 0.0)
        self.assertEqual(
            number_arrows.number_step_value(1_000_000.0, 1, **kwargs),
            1_000_000.0,
        )
        self.assertEqual(number_arrows.number_step_value(10.0, 1, **kwargs), 11.0)

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
