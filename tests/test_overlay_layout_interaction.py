from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest


MODULE_PATH = Path(__file__).parents[1] / "src" / "lib" / "overlay_layout.py"
PACKAGE = "_gesture_overlay_interaction_test"


class Vector:
    def __init__(self, values):
        self.x, self.y = values

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        return Vector((self.x + other.x, self.y + other.y))

    def __sub__(self, other):
        return Vector((self.x - other.x, self.y - other.y))

    def __eq__(self, other):
        return isinstance(other, Vector) and self.x == other.x and self.y == other.y

    @property
    def length_squared(self):
        return self.x ** 2 + self.y ** 2


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_overlay_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[2])]
    for package_name, path in (
            ("src", MODULE_PATH.parents[1]),
            ("src.lib", MODULE_PATH.parent),
            ("utils", MODULE_PATH.parents[2] / "utils"),
    ):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = [str(path)]

    calls = []
    bpy = _module("bpy")
    bpy.context = SimpleNamespace(region=None)
    bpy.ops = SimpleNamespace(
        smoke=SimpleNamespace(run=lambda *_args, **kwargs: calls.append(kwargs)),
    )
    _module(
        "blf",
        size=lambda *_args: None,
        dimensions=lambda _font_id, text: (len(str(text)) * 8.0, 12.0),
    )
    _module(
        "gpu",
        types=SimpleNamespace(),
        shader=SimpleNamespace(),
        matrix=SimpleNamespace(),
    )
    gpu_extras = _module("gpu_extras")
    gpu_extras.__path__ = []
    _module("gpu_extras.batch", batch_for_shader=lambda *_args, **_kwargs: None)
    _module("mathutils", Vector=Vector)
    _module(
        f"{PACKAGE}.utils.public_gpu",
        gpu_draw_begin=lambda: None,
        gpu_draw_end=lambda: None,
    )

    name = f"{PACKAGE}.src.lib.overlay_layout"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, calls


overlay_module, operator_calls = _load_overlay_module()


def _event(event_type, value, *, mouse_x=50, mouse_y=50):
    return SimpleNamespace(
        type=event_type,
        value=value,
        mouse_x=mouse_x,
        mouse_y=mouse_y,
    )


class OverlayInteractionTests(unittest.TestCase):
    def setUp(self):
        operator_calls.clear()
        self.layout = overlay_module.OverlayLayout()
        self.node = overlay_module.OverlayNode(
            "OPERATOR",
            text="Run",
            operator="smoke.run",
            properties=SimpleNamespace(answer=42),
            rect=(0.0, 0.0, 100.0, 24.0),
        )
        self.layout.root.children.append(self.node)
        self.layout._laid_out = True
        self.layout._hover = self.node

    def test_operator_activates_only_after_release_over_same_row(self):
        revision = self.layout.interaction_revision

        self.assertTrue(self.layout.check_event(_event("LEFTMOUSE", "PRESS")))
        self.assertIs(self.layout._pressed, self.node)
        self.assertEqual(self.layout._node_fill(self.node), self.layout.pressed_color)
        self.assertEqual(operator_calls, [])
        self.assertGreater(self.layout.interaction_revision, revision)

        self.assertTrue(self.layout.check_event(_event("LEFTMOUSE", "RELEASE")))
        self.assertIsNone(self.layout._pressed)
        self.assertEqual(operator_calls, [{"answer": 42}])

    def test_release_after_pointer_leaves_cancels_activation(self):
        self.assertTrue(self.layout.check_event(_event("LEFTMOUSE", "PRESS")))
        self.layout._hover = None

        self.assertTrue(self.layout.check_event(_event("LEFTMOUSE", "RELEASE")))
        self.assertIsNone(self.layout._pressed)
        self.assertEqual(operator_calls, [])
        self.assertEqual(self.layout._node_fill(self.node), self.layout.row_color)

    def test_fill_width_stretches_only_requested_column_rows(self):
        self.layout.root.children.clear()
        fill_node = overlay_module.OverlayNode(
            "OPERATOR",
            text="Short",
            fill_width=True,
            size=Vector((40.0, 24.0)),
        )
        natural_node = overlay_module.OverlayNode(
            "OPERATOR",
            text="Longer",
            size=Vector((100.0, 24.0)),
        )
        self.layout.root.children.extend((fill_node, natural_node))
        self.layout.root.size = Vector((100.0, 51.0))

        self.layout._arrange(self.layout.root, 10.0, 80.0)

        self.assertEqual(fill_node.rect, (10.0, 56.0, 110.0, 80.0))
        self.assertEqual(natural_node.rect, (10.0, 29.0, 110.0, 53.0))

    def test_fill_width_row_places_trailing_control_at_right_edge(self):
        self.layout.root.children.clear()
        title = overlay_module.OverlayNode(
            "LABEL",
            text="Select Gesture",
            size=Vector((48.0, 24.0)),
        )
        close = overlay_module.OverlayNode(
            "OPERATOR",
            text="X",
            tooltip="Close Preview",
            size=Vector((20.0, 24.0)),
        )
        title_row = overlay_module.OverlayNode(
            "ROW",
            fill_width=True,
            align_last=True,
            children=[title, close],
            size=Vector((71.0, 24.0)),
        )
        widest_row = overlay_module.OverlayNode(
            "OPERATOR",
            text="Gesture",
            size=Vector((100.0, 24.0)),
        )
        self.layout.root.children.extend((title_row, widest_row))
        self.layout.root.size = Vector((100.0, 51.0))

        self.layout._arrange(self.layout.root, 10.0, 80.0)

        self.assertEqual(title_row.rect, (10.0, 56.0, 110.0, 80.0))
        self.assertEqual(title.rect, (10.0, 56.0, 58.0, 80.0))
        self.assertEqual(close.rect, (90.0, 56.0, 110.0, 80.0))
        self.layout._hover = close
        self.assertEqual(self.layout.hover_tooltip, "Close Preview")

    def test_inactive_alpha_multiplier_does_not_dim_active_or_hover_states(self):
        self.node.alpha_multiplier = 0.1
        self.layout._hover = None
        expected = (
            *self.layout.row_color[:3],
            self.layout.row_color[3] * 0.1,
        )
        self.assertEqual(self.layout._node_fill(self.node), expected)

        self.node.active = True
        self.assertEqual(self.layout._node_fill(self.node), self.layout.active_color)

        self.node.active = False
        self.layout._hover = self.node
        self.assertEqual(self.layout._node_fill(self.node), self.layout.hover_color)

    def test_top_left_region_anchor_includes_drag_offset(self):
        overlay_module.bpy.context.region = SimpleNamespace(
            x=20,
            y=30,
            width=800,
            height=600,
        )
        try:
            self.layout.anchor = "TOP_LEFT_REGION"
            self.layout.padding = 7
            self.layout.root.size = Vector((100.0, 50.0))
            self.layout.offset_position = Vector((10.0, -5.0))

            self.assertEqual(
                self.layout._anchor_origin(),
                Vector((44.0, 611.0)),
            )
        finally:
            overlay_module.bpy.context.region = None

    def test_root_surface_can_be_dragged(self):
        self.layout.root_draggable = True
        self.node.kind = "LABEL"
        self.layout.root.rect = (0.0, 0.0, 100.0, 24.0)
        self.layout.sync_input((0.0, 0.0), (50.0, 12.0))

        self.assertTrue(self.layout.check_event(
            _event("LEFTMOUSE", "PRESS", mouse_x=50, mouse_y=12)
        ))
        self.assertTrue(self.layout.check_event(
            _event("MOUSEMOVE", "NOTHING", mouse_x=70, mouse_y=2)
        ))
        self.assertEqual(self.layout.drag_offset, Vector((20.0, -10.0)))
        self.assertEqual(self.layout.drag_revision, 1)
        self.assertTrue(self.layout.check_event(
            _event("LEFTMOUSE", "RELEASE", mouse_x=70, mouse_y=2)
        ))
        self.assertIsNone(self.layout._drag_mouse)

    def test_root_dragging_does_not_steal_operator_clicks(self):
        self.layout.root_draggable = True
        self.layout.root.rect = (0.0, 0.0, 100.0, 24.0)

        self.assertTrue(self.layout.check_event(
            _event("LEFTMOUSE", "PRESS", mouse_x=50, mouse_y=12)
        ))

        self.assertIsNone(self.layout._drag_mouse)
        self.assertIs(self.layout._pressed, self.node)

    def test_sync_input_reports_hover_changes_for_redraw(self):
        self.layout.mouse_position = Vector((50.0, 12.0))
        self.node.tooltip = "Close Preview"

        changed = self.layout.sync_input((0.0, 0.0), (150.0, 12.0))

        self.assertTrue(changed)
        self.assertIsNone(self.layout._hover)
        self.assertEqual(self.layout.hover_tooltip, "")

    def test_hover_tooltip_geometry_stays_inside_owner_region(self):
        overlay_module.bpy.context.region = SimpleNamespace(
            x=20,
            y=30,
            width=240,
            height=180,
        )
        try:
            self.node.tooltip = "Close Preview"
            self.node.rect = (210.0, 110.0, 250.0, 134.0)
            self.layout._hover = self.node

            text, _size, _pad, _line_height, rect = (
                self.layout._tooltip_geometry()
            )

            self.assertEqual(text, "Close Preview")
            self.assertGreaterEqual(rect[0], 22.0)
            self.assertLessEqual(rect[2], 258.0)
            self.assertGreaterEqual(rect[1], 32.0)
            self.assertLessEqual(rect[3], 208.0)
        finally:
            overlay_module.bpy.context.region = None

    def test_sdf_shader_matches_builtin_overlay_color_conversion(self):
        source = overlay_module._FRAG_SRC

        self.assertIn("gesture_srgb_to_framebuffer_space", source)
        self.assertIn(
            "vec4 col = gesture_srgb_to_framebuffer_space(finalColor);",
            source,
        )
        self.assertIn("fragColor = col;", source)


if __name__ == "__main__":
    unittest.main()
