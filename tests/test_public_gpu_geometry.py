from __future__ import annotations

import contextlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "utils" / "public_gpu.py"
PACKAGE = "_public_gpu_geometry_test"


class FakeMatrixApi:
    @staticmethod
    def push_pop():
        return contextlib.nullcontext()

    @staticmethod
    def translate(_position):
        return None

    @staticmethod
    def get_model_view_matrix():
        return "model-view"


class PublicGpuGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = (
            "blf",
            "gpu",
            "gpu_extras",
            "gpu_extras.batch",
            PACKAGE,
            f"{PACKAGE}.utils",
            f"{PACKAGE}.utils.color",
            f"{PACKAGE}.utils.gpu_layout_batch",
        )
        cls.old_modules = {name: sys.modules.get(name) for name in names}

        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(MODULE_PATH.parents[1])]
        utils = types.ModuleType(f"{PACKAGE}.utils")
        utils.__path__ = [str(MODULE_PATH.parent)]
        color = types.ModuleType(f"{PACKAGE}.utils.color")
        color.clear_color_cache = lambda: None
        color.color_to_gpu = tuple
        color.color_to_srgb = tuple
        color.linear_to_srgb_tuple = tuple

        layout_batch = types.ModuleType(f"{PACKAGE}.utils.gpu_layout_batch")

        class FakeLayoutBatch:
            instances = []

            def __init__(self):
                self.events = []
                self.flush_count = 0
                self.flush_error = None
                self.__class__.instances.append(self)

            def add_fill(self, *args):
                self.events.append(("fill", args))

            def add_stroke(self, *args):
                self.events.append(("stroke", args))

            def add_image(self, *args):
                self.events.append(("image", args))

            def add_text(self, *args):
                self.events.append(("text", args))

            def flush(self):
                self.flush_count += 1
                if self.flush_error is not None:
                    raise self.flush_error

        layout_batch.GpuLayoutBatch = FakeLayoutBatch
        cls.fake_layout_batch = FakeLayoutBatch

        gpu = types.ModuleType("gpu")
        gpu.matrix = FakeMatrixApi()
        gpu_extras = types.ModuleType("gpu_extras")
        batch = types.ModuleType("gpu_extras.batch")
        batch.batch_for_shader = lambda *_args, **_kwargs: None

        sys.modules.update({
            "blf": types.ModuleType("blf"),
            "gpu": gpu,
            "gpu_extras": gpu_extras,
            "gpu_extras.batch": batch,
            PACKAGE: package,
            f"{PACKAGE}.utils": utils,
            color.__name__: color,
            layout_batch.__name__: layout_batch,
        })

        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.utils.public_gpu",
            MODULE_PATH,
        )
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop(f"{PACKAGE}.utils.public_gpu", None)
        for name, old in cls.old_modules.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old

    def test_radius_is_clamped_only_to_rectangle_dimensions(self):
        with mock.patch.object(self.module, "_draw_rounded_fill") as draw_fill:
            self.module.PublicGpu.draw_rounded_rectangle_area(
                (0, 0), radius=30, width=100, height=20,
            )
        self.assertEqual(draw_fill.call_args.args[2], 10.0)

        with mock.patch.object(self.module, "_draw_rounded_fill") as draw_fill:
            self.module.PublicGpu.draw_rounded_rectangle_area(
                (0, 0), radius=-5, width=100, height=20,
            )
        self.assertEqual(draw_fill.call_args.args[2], 0.0)

    def test_layout_batch_collects_primitives_and_reuses_nested_owner(self):
        self.fake_layout_batch.instances.clear()
        texture = object()

        with self.module.layout_gpu_batch() as outer:
            with self.module.layout_gpu_batch() as inner:
                self.assertIs(inner, outer)
                self.module.PublicGpu.draw_rounded_rectangle_area(
                    (5, 6),
                    color=(0.1, 0.2, 0.3, 0.4),
                    radius=9,
                    width=20,
                    height=10,
                )
                self.module.draw_line(
                    ((0, 0), (1, 1)),
                    (1, 1, 1, 1),
                    2,
                )
                self.module.PublicGpu.draw_image((2, 3), 8, 9, texture)
                self.module.PublicGpu.draw_text("Label", position=(4, 5))

        self.assertEqual(len(self.fake_layout_batch.instances), 1)
        batch = self.fake_layout_batch.instances[0]
        self.assertEqual(
            [event[0] for event in batch.events],
            ["fill", "stroke", "image", "text"],
        )
        self.assertEqual(batch.flush_count, 1)
        self.assertEqual(batch.events[0][1][-1], "model-view")
        self.assertEqual(batch.events[1][1][-1], "model-view")
        self.assertEqual(batch.events[2][1][-1], "model-view")
        self.assertEqual(batch.events[3][1][-1], "model-view")

    def test_explicit_layout_flush_preserves_batch_owner(self):
        self.fake_layout_batch.instances.clear()
        with self.module.layout_gpu_batch() as batch:
            self.module.flush_layout_gpu_batch()
            self.assertIs(self.module._LAYOUT_GPU_BATCH, batch)

        self.assertEqual(batch.flush_count, 2)

    def test_layout_batch_preserves_primary_draw_exception(self):
        self.fake_layout_batch.instances.clear()

        with self.assertRaisesRegex(ValueError, "primary"):
            with self.module.layout_gpu_batch() as batch:
                batch.flush_error = RuntimeError("secondary")
                raise ValueError("primary")

        self.assertEqual(batch.flush_count, 1)
        self.assertIsNone(self.module._LAYOUT_GPU_BATCH)

    def test_outlined_rectangle_uses_the_same_dimension_clamp(self):
        with (
            mock.patch.object(self.module, "_draw_rounded_fill") as draw_fill,
            mock.patch.object(self.module, "draw_line"),
        ):
            self.module.PublicGpu.draw_rounded_rectangle_outlined(
                (0, 0), radius=30, width=18, height=100,
            )
        self.assertEqual(draw_fill.call_args.args[2], 9.0)

    def test_corner_mask_squares_only_the_requested_aligned_edges(self):
        points = self.module.get_rounded_rectangle_vertex(
            8,
            100,
            30,
            12,
            (True, False, False, True),
        )

        self.assertIn((50.0, 15.0), points)
        self.assertIn((50.0, -15.0), points)
        self.assertNotIn((-50.0, 15.0), points)
        self.assertNotIn((-50.0, -15.0), points)

    def test_corner_mask_is_forwarded_to_fill_and_outline(self):
        corner_mask = (True, False, False, True)
        with (
            mock.patch.object(self.module, "_draw_rounded_fill") as draw_fill,
            mock.patch.object(self.module, "draw_line"),
        ):
            self.module.PublicGpu.draw_rounded_rectangle_outlined(
                (0, 0),
                radius=6,
                width=40,
                height=20,
                corner_mask=corner_mask,
            )
        self.assertEqual(draw_fill.call_args.args[-1], corner_mask)

    def test_outline_has_symmetric_inclusive_tangent_endpoints(self):
        radius = 12
        width = 100
        height = 40
        segments = 12
        points = self.module.get_rounded_rectangle_vertex(
            radius, width, height, segments,
        )
        count = self.module._round_rect_segments(radius, segments)

        self.assertEqual(len(points), 4 * (count + 1))
        expected_tangents = (
            (50, 8), (38, 20),
            (-38, 20), (-50, 8),
            (-50, -8), (-38, -20),
            (38, -20), (50, -8),
        )
        actual_tangents = []
        for corner in range(4):
            start = corner * (count + 1)
            actual_tangents.extend((points[start], points[start + count]))
        for actual, expected in zip(actual_tangents, expected_tangents):
            self.assertAlmostEqual(actual[0], expected[0])
            self.assertAlmostEqual(actual[1], expected[1])

        rounded = {(round(x, 8), round(y, 8)) for x, y in points}
        self.assertEqual(min(x for x, _y in points), -50)
        self.assertEqual(max(x for x, _y in points), 50)
        self.assertEqual(min(y for _x, y in points), -20)
        self.assertEqual(max(y for _x, y in points), 20)
        for x, y in rounded:
            self.assertIn((-x, y), rounded)
            self.assertIn((x, -y), rounded)
            self.assertIn((-x, -y), rounded)

    def test_annotation_row_flips_above_a_low_anchor_and_stays_in_viewport(self):
        text_module = types.ModuleType(f"{PACKAGE}.utils.blf_text")
        text_module.measure_text = lambda text, _size: (len(str(text)) * 6.0, 12.0)
        text_module.wrap_text = (
            lambda text, _width, _size, max_lines=2: [str(text)][:max_lines]
        )
        with (
            mock.patch.dict(sys.modules, {text_module.__name__: text_module}),
            mock.patch.object(
                self.module.PublicGpu,
                "draw_rounded_rectangle_outlined",
            ),
            mock.patch.object(
                self.module.PublicGpu,
                "draw_rounded_rectangle_area",
            ),
            mock.patch.object(self.module.PublicGpu, "draw_text"),
        ):
            rect = self.module.PublicGpu.draw_annotation_row(
                "Native operator description",
                anchor_rect=(50.0, 5.0, 150.0, 25.0),
                viewport_size=(220.0, 140.0),
                size=12.0,
            )

        self.assertIsNotNone(rect)
        self.assertGreater(rect[1], 25.0)
        self.assertGreaterEqual(rect[0], 0.0)
        self.assertLessEqual(rect[2], 220.0)
        self.assertLessEqual(rect[3], 140.0)

    def test_runtime_tooltip_stays_in_viewport_during_reveal(self):
        text_module = types.ModuleType(f"{PACKAGE}.utils.blf_text")
        text_module.measure_text = lambda text, _size: (len(str(text)) * 6.0, 12.0)
        text_module.wrap_text = (
            lambda text, _width, _size, max_lines=2: [str(text)][:max_lines]
        )
        tooltip = types.SimpleNamespace(
            title="Add Cube",
            description="Construct a cube mesh",
            details=(types.SimpleNamespace(label="Python", value="bpy.ops.mesh.primitive_cube_add()"),),
            issues=("Unavailable in this context",),
        )
        with (
            mock.patch.dict(sys.modules, {text_module.__name__: text_module}),
            mock.patch.object(
                self.module.PublicGpu,
                "draw_rounded_rectangle_outlined",
            ),
            mock.patch.object(self.module.PublicGpu, "draw_text"),
        ):
            rect = self.module.PublicGpu.draw_runtime_tooltip(
                tooltip,
                anchor_rect=(60.0, 8.0, 160.0, 28.0),
                viewport_size=(240.0, 180.0),
                size=12.0,
                reveal=0.5,
            )

        self.assertIsNotNone(rect)
        self.assertGreater(rect[1], 28.0)
        self.assertGreaterEqual(rect[0], 0.0)
        self.assertLessEqual(rect[2], 240.0)
        self.assertLessEqual(rect[3], 180.0)


if __name__ == "__main__":
    unittest.main()
