import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / 'utils' / 'layout_alignment.py'
SPEC = importlib.util.spec_from_file_location('gesture_layout_alignment', MODULE_PATH)
layout_alignment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout_alignment)


class LayoutAlignmentTests(unittest.TestCase):
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

    def test_vertical_alignment(self):
        self.assertEqual(
            layout_alignment.resolve_layout_cross_axis(20, 60, 'CENTER'),
            (20.0, 20.0),
        )
        self.assertEqual(
            layout_alignment.resolve_layout_cross_axis(20, 60, 'RIGHT'),
            (40.0, 20.0),
        )
        self.assertEqual(
            layout_alignment.resolve_layout_cross_axis(20, 60, 'EXPAND'),
            (0.0, 60.0),
        )


if __name__ == '__main__':
    unittest.main()
