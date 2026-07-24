from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "gpu.py"


class Vector(tuple):
    pass


class Matrix:
    def __init__(self, rows):
        self.rows = tuple(tuple(float(value) for value in row) for row in rows)

    def __matmul__(self, other):
        if isinstance(other, Matrix):
            return Matrix([
                [
                    sum(self.rows[row][k] * other.rows[k][column] for k in range(3))
                    for column in range(3)
                ]
                for row in range(3)
            ])
        x, y = other[0], other[1]
        return Vector((
            self.rows[0][0] * x + self.rows[0][1] * y + self.rows[0][2],
            self.rows[1][0] * x + self.rows[1][1] * y + self.rows[1][2],
            0.0,
        ))


def translate(x, y):
    return Matrix(((1, 0, x), (0, 1, y), (0, 0, 1)))


def scale(x, y):
    return Matrix(((x, 0, 0), (0, y, 0), (0, 0, 1)))


class GpuRectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_gpu = sys.modules.get("gpu")
        cls.old_mathutils = sys.modules.get("mathutils")
        gpu = types.ModuleType("gpu")
        gpu.matrix = types.SimpleNamespace(get_model_view_matrix=lambda: cls.matrix)
        mathutils = types.ModuleType("mathutils")
        mathutils.Vector = Vector
        sys.modules["gpu"] = gpu
        sys.modules["mathutils"] = mathutils
        spec = importlib.util.spec_from_file_location("gpu_rect_test_module", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        if cls.old_gpu is None:
            sys.modules.pop("gpu", None)
        else:
            sys.modules["gpu"] = cls.old_gpu
        if cls.old_mathutils is None:
            sys.modules.pop("mathutils", None)
        else:
            sys.modules["mathutils"] = cls.old_mathutils

    def test_nested_non_uniform_scale_transforms_all_rectangle_corners(self):
        self.__class__.matrix = (
            translate(100, 200)
            @ scale(2, 0.5)
            @ translate(7, -11)
            @ scale(0.75, 4)
            @ translate(4, -6)
        )

        rect = self.module.get_current_2d_rect((0.0, -20.0, 80.0, 0.0))

        self.assertEqual(rect, [120.0, 142.5, 240.0, 182.5])

    def test_reflection_still_returns_ordered_axis_aligned_bounds(self):
        matrix = translate(10, 20) @ scale(-2, 3)
        rect = self.module.transform_2d_rect(matrix, (1, -2, 5, 4))
        self.assertEqual(rect, [0.0, 14.0, 8.0, 32.0])


if __name__ == "__main__":
    unittest.main()
