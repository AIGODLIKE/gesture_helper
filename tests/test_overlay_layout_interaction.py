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
    _module("blf")
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


def _event(event_type, value):
    return SimpleNamespace(
        type=event_type,
        value=value,
        mouse_x=50,
        mouse_y=50,
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


if __name__ == "__main__":
    unittest.main()
