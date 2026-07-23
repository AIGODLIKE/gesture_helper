from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "ops" / "menu.py"
PACKAGE = "gesture_helper_menu_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_menu_module():
    root = _module(PACKAGE)
    root.__path__ = []
    for package_name in ("ops", "gesture", "utils"):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = []

    bpy = _module("bpy")
    bpy_app = _module("bpy.app")
    _module("bpy.app.translations", pgettext=lambda text: text)
    _module("bpy.props", StringProperty=lambda: None)
    bpy.app = bpy_app

    class GestureExecutor:
        pass

    class GestureMenuRuntime:
        pass

    class PublicOperator:
        pass

    _module(
        f"{PACKAGE}.gesture.gesture_executor",
        GestureExecutor=GestureExecutor,
    )
    _module(
        f"{PACKAGE}.gesture.menu",
        GestureMenuRuntime=GestureMenuRuntime,
    )
    _module(
        f"{PACKAGE}.utils.adapter",
        operator_setattr=setattr,
    )
    _module(
        f"{PACKAGE}.utils.public",
        PublicOperator=PublicOperator,
        debug_print=lambda *args, **kwargs: None,
    )

    name = f"{PACKAGE}.ops.menu"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


menu_module = _load_menu_module()


class FakeOperator:
    def __init__(self, pointer, identifier="WM_OT_external"):
        self._pointer = pointer
        self.bl_idname = identifier

    def as_pointer(self):
        return self._pointer


class FakeWindow:
    def __init__(self, operators=()):
        self.modal_operators = list(operators)


class FakeContext:
    def __init__(self, window):
        self.window = window


class MenuModalBaselineTests(unittest.TestCase):
    def make_menu(self, pointer=100):
        menu = menu_module.GestureMenuOperator()
        menu.as_pointer = lambda: pointer
        return menu

    def set_baseline(self, menu, window):
        menu._menu_initial_modal_keys = frozenset(
            key for _operator, key in menu._window_modal_operators(window)
        )

    def test_existing_modal_is_not_treated_as_menu_launched(self):
        baseline_operator = FakeOperator(1)
        window = FakeWindow([baseline_operator])
        menu = self.make_menu()
        self.set_baseline(menu, window)

        window.modal_operators = [FakeOperator(1), menu]

        self.assertFalse(menu._has_external_modal(FakeContext(window)))

    def test_new_modal_is_detected_until_it_finishes(self):
        window = FakeWindow([FakeOperator(1)])
        menu = self.make_menu()
        self.set_baseline(menu, window)

        window.modal_operators = [FakeOperator(1), menu, FakeOperator(2)]
        self.assertTrue(menu._has_external_modal(FakeContext(window)))

        window.modal_operators = [FakeOperator(1), menu]
        self.assertFalse(menu._has_external_modal(FakeContext(window)))

    def test_self_and_duplicate_menu_operators_are_ignored(self):
        window = FakeWindow()
        menu = self.make_menu()
        self.set_baseline(menu, window)
        window.modal_operators = [
            menu,
            FakeOperator(101, "wm.gesture_menu"),
            FakeOperator(102, "WM_OT_gesture_menu"),
        ]

        self.assertFalse(menu._has_external_modal(FakeContext(window)))

    def test_missing_modal_collection_is_compatible(self):
        menu = self.make_menu()
        window = object()

        self.assertEqual(menu._window_modal_operators(window), ())
        self.assertFalse(menu._has_external_modal(FakeContext(window)))


if __name__ == "__main__":
    unittest.main()
