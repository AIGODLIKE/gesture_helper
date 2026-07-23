from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "ops" / "quick_add" / "gesture_preview.py"
PACKAGE = "gesture_helper_preview_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_preview_module():
    for package_name in (
        PACKAGE,
        f"{PACKAGE}.ops",
        f"{PACKAGE}.ops.quick_add",
        f"{PACKAGE}.gesture",
        f"{PACKAGE}.utils",
    ):
        package = _module(package_name)
        package.__path__ = []

    bpy = _module("bpy")
    bpy.types = types.SimpleNamespace(Context=object, Event=object)
    _module("bpy.props", StringProperty=lambda: None)

    class Vector(tuple):
        def __new__(cls, value):
            return super().__new__(cls, value)

    _module("mathutils", Vector=Vector)

    class DrawGpu:
        pass

    class GestureGpuDraw:
        pass

    class GestureHandle:
        pass

    class GestureRuntimeMixin:
        pass

    class PublicOperator:
        pass

    _module(f"{PACKAGE}.ops.quick_add.draw_gpu", DrawGpu=DrawGpu)
    _module(f"{PACKAGE}.gesture.gesture_draw_gpu", GestureGpuDraw=GestureGpuDraw)
    _module(f"{PACKAGE}.gesture.gesture_handle", GestureHandle=GestureHandle)
    _module(f"{PACKAGE}.gesture.gesture_input", refresh_snapshot=lambda *_args: None)
    _module(
        f"{PACKAGE}.gesture.preview_input",
        PreviewGestureInputProcessor=type("PreviewGestureInputProcessor", (), {}),
    )
    _module(f"{PACKAGE}.gesture.gesture_runtime", GestureRuntimeMixin=GestureRuntimeMixin)
    _module(
        f"{PACKAGE}.gesture.gesture_session",
        GestureSession=type("GestureSession", (), {}),
    )
    _module(f"{PACKAGE}.utils.adapter", operator_setattr=setattr)
    _module(f"{PACKAGE}.utils.public", PublicOperator=PublicOperator)
    _module(
        f"{PACKAGE}.utils.session_state",
        SessionState=type("SessionState", (), {"gesture_preview_active": False}),
    )

    name = f"{PACKAGE}.ops.quick_add.gesture_preview"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


preview_module = _load_preview_module()


class FakeRegion:
    def __init__(self, region_type):
        self.type = region_type


class FakeArea:
    def __init__(self, area_type, region_types=("WINDOW",)):
        self.type = area_type
        self.regions = [FakeRegion(region_type) for region_type in region_types]


class FakeScreen:
    def __init__(self, areas):
        self.areas = areas


class FakeWindow:
    def __init__(self, areas):
        self.screen = FakeScreen(areas)


class PreviewContextTests(unittest.TestCase):
    def test_cross_window_override_omits_temporary_screen(self):
        preferences_window = FakeWindow([FakeArea("PREFERENCES")])
        view_area = FakeArea("VIEW_3D")
        view_window = FakeWindow([view_area])
        context = types.SimpleNamespace(
            window_manager=types.SimpleNamespace(
                windows=[preferences_window, view_window],
            ),
            window=preferences_window,
        )

        override = preview_module.GesturePreview.find_view3d_context(context)

        self.assertEqual(set(override), {"window", "area", "region"})
        self.assertIs(override["window"], view_window)
        self.assertIs(override["area"], view_area)
        self.assertEqual(override["region"].type, "WINDOW")

    def test_current_window_is_preferred_when_it_has_a_view(self):
        other_area = FakeArea("VIEW_3D")
        other_window = FakeWindow([other_area])
        current_area = FakeArea("VIEW_3D")
        current_window = FakeWindow([current_area])
        context = types.SimpleNamespace(
            window_manager=types.SimpleNamespace(
                windows=[other_window, current_window],
            ),
            window=current_window,
        )

        override = preview_module.GesturePreview.find_view3d_context(context)

        self.assertIs(override["window"], current_window)
        self.assertIs(override["area"], current_area)


if __name__ == "__main__":
    unittest.main()
