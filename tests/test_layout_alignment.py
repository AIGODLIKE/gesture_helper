import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / 'utils' / 'layout_alignment.py'
SPEC = importlib.util.spec_from_file_location('gesture_layout_alignment', MODULE_PATH)
layout_alignment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout_alignment)


class LayoutAlignmentTests(unittest.TestCase):
    def test_separator_line_width_matches_menu_and_gesture_thickness(self):
        self.assertEqual(layout_alignment.separator_line_width(2, 1.0), 0.8)
        self.assertEqual(layout_alignment.separator_line_width(2, 2.0), 1.6)
        self.assertEqual(layout_alignment.separator_line_width(1, 0.5), 0.75)

    def test_nested_layout_group_restores_all_outer_corners(self):
        inherited = (False, False, False, False)
        self.assertEqual(
            layout_alignment.layout_group_corner_mask(True, inherited),
            layout_alignment.ROUND_CORNERS_ALL,
        )
        self.assertEqual(
            layout_alignment.layout_group_corner_mask(False, inherited),
            inherited,
        )

    def test_aligned_populated_box_has_no_inner_inset(self):
        self.assertEqual(
            layout_alignment.resolve_box_inset(True, True, 8, 5),
            (0.0, 0.0),
        )

    def test_unaligned_or_empty_box_keeps_text_inset(self):
        self.assertEqual(
            layout_alignment.resolve_box_inset(False, True, 8, 5),
            (8.0, 5.0),
        )
        self.assertEqual(
            layout_alignment.resolve_box_inset(True, False, 8, 5),
            (8.0, 5.0),
        )

    def test_single_extension_action_fills_the_complete_outer_surface(self):
        self.assertEqual(
            layout_alignment.resolve_extension_row_bounds(
                100, 20, 8, 6, fill_outer_surface=True,
            ),
            (-8.0, -26.0, 108.0, 6.0),
        )

    def test_multi_row_extension_action_keeps_shared_panel_inset(self):
        self.assertEqual(
            layout_alignment.resolve_extension_row_bounds(
                100, 20, 8, 6,
            ),
            (-2.0, -20.0, 102.0, 0.0),
        )

    def test_expand_uses_native_proportional_widths(self):
        result = layout_alignment.resolve_layout_line(
            (10, 30), available=62, gap=2, alignment='EXPAND',
        )
        self.assertEqual(result, ((0.0, 15.0), (17.0, 45.0)))

    def test_center_and_right_keep_intrinsic_widths(self):
        center = layout_alignment.resolve_layout_line(
            (10, 30), available=60, gap=2, alignment='CENTER',
        )
        right = layout_alignment.resolve_layout_line(
            (10, 30), available=60, gap=2, alignment='RIGHT',
        )
        self.assertEqual(center, ((9.0, 10.0), (21.0, 30.0)))
        self.assertEqual(right, ((18.0, 10.0), (30.0, 30.0)))

    def test_overflow_is_proportionally_compressed(self):
        result = layout_alignment.resolve_layout_line(
            (10, 30), available=30, gap=2, alignment='LEFT',
        )
        self.assertEqual(result, ((0.0, 7.0), (9.0, 21.0)))

    def test_vertical_layout_matches_native_full_width_items(self):
        for alignment in ('EXPAND', 'LEFT', 'CENTER', 'RIGHT'):
            self.assertEqual(
                layout_alignment.resolve_layout_cross_axis(20, 60, alignment),
                (0.0, 60.0),
            )

    def test_hover_blend_preserves_property_slider_contrast(self):
        background = (0.04, 0.05, 0.06, 0.97)
        slider = (0.05, 0.24, 0.42, 0.92)
        accent = (0.03, 0.23, 0.52, 1.0)
        hovered_background = layout_alignment.blend_layout_hover_color(
            background, accent,
        )
        hovered_slider = layout_alignment.blend_layout_hover_color(
            slider, accent,
        )

        self.assertNotEqual(hovered_background, background)
        self.assertEqual(hovered_background[3], background[3])
        self.assertEqual(hovered_slider[3], slider[3])
        for index in range(3):
            self.assertAlmostEqual(
                hovered_slider[index] - hovered_background[index],
                (slider[index] - background[index]) * 0.65,
            )

    def test_aligned_row_keeps_only_the_group_outer_corners(self):
        self.assertEqual(
            layout_alignment.aligned_child_corner_masks(3, horizontal=True),
            (
                (True, False, False, True),
                (False, False, False, False),
                (False, True, True, False),
            ),
        )

    def test_nested_aligned_rows_inherit_column_outer_corners(self):
        top, middle, bottom = layout_alignment.aligned_child_corner_masks(
            3,
            horizontal=False,
        )
        self.assertEqual(
            layout_alignment.aligned_child_corner_masks(3, horizontal=True, outer=top),
            (
                (True, False, False, False),
                (False, False, False, False),
                (False, True, False, False),
            ),
        )
        self.assertEqual(middle, (False, False, False, False))
        self.assertEqual(
            layout_alignment.aligned_child_corner_masks(3, horizontal=True, outer=bottom),
            (
                (False, False, False, True),
                (False, False, False, False),
                (False, False, True, False),
            ),
        )

    def test_separator_keeps_internal_aligned_corners_square(self):
        self.assertEqual(
            layout_alignment.aligned_surface_corner_masks(
                (True, True, False, True, True),
                horizontal=False,
            ),
            (
                (True, True, False, False),
                (False, False, False, False),
                (False, False, False, False),
                (False, False, False, False),
                (False, False, True, True),
            ),
        )


if __name__ == '__main__':
    unittest.main()
