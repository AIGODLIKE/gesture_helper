from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "menu.py"
PACKAGE = "_gesture_menu_redraw_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_menu_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    for package_name, path in (
            ("gesture", MODULE_PATH.parent),
            ("utils", MODULE_PATH.parents[1] / "utils"),
            ("element", MODULE_PATH.parents[1] / "element"),
    ):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = [str(path)]

    bpy = _module("bpy")
    bpy.context = types.SimpleNamespace()

    _module(
        f"{PACKAGE}.utils.blf_text",
        measure_text=lambda *_args, **_kwargs: (0.0, 0.0),
    )
    _module(
        f"{PACKAGE}.utils.color",
        color_to_srgb=lambda color: color,
    )
    _module(
        f"{PACKAGE}.utils.gesture_items",
        get_gesture_extension_items=lambda _items: (),
        poll_context_fingerprint=lambda: (),
    )

    class PublicGpu:
        pass

    _module(
        f"{PACKAGE}.utils.public_gpu",
        PublicGpu=PublicGpu,
        gpu_draw_begin=lambda: None,
        gpu_draw_end=lambda: None,
    )
    _module(
        f"{PACKAGE}.element.element_status",
        ElementStatus=types.SimpleNamespace(
            VALID=types.SimpleNamespace(is_error=False),
        ),
        get_element_status_info=lambda _element, **_kwargs: None,
    )

    name = f"{PACKAGE}.gesture.menu"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


menu_module = _load_menu_module()


class FakeRegion:
    def __init__(self, region_type):
        self.type = region_type
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class FakeArea:
    def __init__(self, regions):
        self.regions = regions
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class MenuRedrawScopeTests(unittest.TestCase):
    @staticmethod
    def _metrics():
        return menu_module.MenuMetrics(
            scale=1.0,
            font_size=12.0,
            line_height=14.0,
            row_height=24.0,
            separator_height=8.0,
            header_height=24.0,
            pad_x=10.0,
            gap=6.0,
            radius=4.0,
            min_width=180.0,
            max_width=440.0,
            flyout_gap=5.0,
            border_width=1.0,
        )

    @staticmethod
    def _colors():
        return menu_module.MenuColors(
            background=(0.08, 0.08, 0.08, 1.0),
            header=(0.1, 0.1, 0.1, 1.0),
            hover=(0.1, 0.3, 0.6, 1.0),
            text=(0.8, 0.8, 0.8, 1.0),
            text_hover=(1.0, 1.0, 1.0, 1.0),
            text_disabled=(0.4, 0.4, 0.4, 1.0),
            outline=(0.2, 0.2, 0.2, 1.0),
            separator=(0.2, 0.2, 0.2, 1.0),
            shadow=(0.0, 0.0, 0.0, 0.3),
            error=(0.72, 0.08, 0.06, 0.9),
            warning=(0.92, 0.48, 0.06, 0.95),
        )

    def test_error_row_uses_red_background_and_white_text(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        status = types.SimpleNamespace(is_error=True)
        row = menu_module.MenuRow(
            None,
            "Broken",
            "OPERATOR",
            enabled=False,
            status_info=types.SimpleNamespace(status=status, badge="OP"),
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        colors = self._colors()

        runtime._draw_row(row, self._metrics(), colors)

        self.assertEqual(
            runtime.draw_rounded_rectangle_area.call_args.kwargs["color"],
            colors.error,
        )
        self.assertEqual(
            runtime.draw_text.call_args.kwargs["color"],
            colors.text_hover,
        )

    def test_menu_redraw_targets_only_owner_window_region(self):
        ui_region = FakeRegion("UI")
        window_region = FakeRegion("WINDOW")
        area = FakeArea([ui_region, window_region])
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_area = area

        runtime._tag_menu_redraw()

        self.assertEqual(window_region.redraws, 1)
        self.assertEqual(ui_region.redraws, 0)
        self.assertEqual(area.redraws, 0)

    def test_menu_redraw_has_no_whole_area_fallback(self):
        ui_region = FakeRegion("UI")
        area = FakeArea([ui_region])
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_area = area

        runtime._tag_menu_redraw()

        self.assertEqual(ui_region.redraws, 0)
        self.assertEqual(area.redraws, 0)


if __name__ == "__main__":
    unittest.main()
