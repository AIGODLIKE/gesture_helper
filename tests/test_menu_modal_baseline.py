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
        def _registered_menu_for_gesture(self, _gesture):
            return None

        def _menu_is_obscured_at(self, _point):
            return False

        def _menu_is_topmost(self):
            return True

        def _clear_menu_hover(self):
            return False

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


class UnreadableRnaOperator:
    bl_rna = object()
    bl_idname = "WM_OT_unreadable"

    def as_pointer(self):
        raise ReferenceError("removed")


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
        menu._menu_mouse = lambda event: getattr(event, "point", None)
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

    def test_existing_gesture_menu_is_reused_instead_of_starting_another(self):
        menu = self.make_menu()
        gesture = object()
        existing = types.SimpleNamespace(_reuse_menu_runtime=lambda: None)
        existing._reuse_menu_runtime = lambda: setattr(existing, 'reused', True)
        menu._registered_menu_for_gesture = lambda candidate: (
            existing if candidate is gesture else None
        )

        self.assertTrue(menu._activate_existing_menu(gesture))
        self.assertTrue(existing.reused)
        self.assertFalse(menu._activate_existing_menu(object()))

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

    def test_unreadable_rna_operator_is_not_misclassified_by_wrapper_id(self):
        menu = self.make_menu()
        window = FakeWindow([UnreadableRnaOperator()])

        self.assertEqual(menu._window_modal_operators(window), ())
        self.assertFalse(menu._has_external_modal(FakeContext(window)))

    def test_pinned_menu_passes_outside_click_without_closing(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._ensure_layout = lambda **_kwargs: None
        menu._menu_close_hit = lambda _event: False
        menu._menu_header_hit = lambda _event: False
        menu._menu_clicked_row = lambda _event: None
        menu._menu_mouse = lambda event: event.point
        menu._menu_contains = lambda _point: False
        menu._close_menu_enum_dropdown = lambda: False
        menu._menu_keep_open = lambda: True
        closes = []
        menu._begin_menu_close = lambda: closes.append(True)
        event = types.SimpleNamespace(
            type="LEFTMOUSE",
            value="PRESS",
            point=(500.0, 500.0),
        )

        result = menu.modal(FakeContext(window), event)

        self.assertEqual(result, {'PASS_THROUGH'})
        self.assertEqual(closes, [])

    def test_unpinned_menu_closes_after_outside_click(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._ensure_layout = lambda **_kwargs: None
        menu._menu_close_hit = lambda _event: False
        menu._menu_header_hit = lambda _event: False
        menu._menu_clicked_row = lambda _event: None
        menu._menu_mouse = lambda event: event.point
        menu._menu_contains = lambda _point: False
        menu._close_menu_enum_dropdown = lambda: False
        menu._menu_keep_open = lambda: False
        closes = []
        menu._begin_menu_close = lambda: closes.append(True)
        event = types.SimpleNamespace(
            type="LEFTMOUSE",
            value="PRESS",
            point=(500.0, 500.0),
        )

        result = menu.modal(FakeContext(window), event)

        self.assertEqual(result, {'PASS_THROUGH'})
        self.assertEqual(closes, [True])

    def test_obscured_pointer_event_passes_through_without_hovering_old_menu(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._menu_mouse = lambda event: event.point
        menu._menu_is_obscured_at = lambda _point: True
        changes = []
        menu._clear_menu_hover = lambda: changes.append('clear-hover') or True
        menu._clear_menu_press = lambda: changes.append('clear-press') or False
        menu._tag_menu_redraw = lambda: changes.append('redraw')
        menu._update_menu_hover = lambda _event: changes.append('hover')
        event = types.SimpleNamespace(
            type='MOUSEMOVE',
            value='NOTHING',
            point=(10.0, 10.0),
        )

        result = menu.modal(FakeContext(window), event)

        self.assertEqual(result, {'PASS_THROUGH'})
        self.assertEqual(changes, ['clear-hover', 'clear-press', 'redraw'])

    def test_obscured_backspace_does_not_reset_an_older_menu(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._menu_mouse = lambda event: event.point
        menu._menu_is_obscured_at = lambda _point: True
        menu._clear_menu_hover = lambda: True
        menu._clear_menu_press = lambda: False
        menu._tag_menu_redraw = lambda: None
        resets = []
        menu._menu_hovered_row = type("Row", (), {
            "enabled": True,
            "kind": "PROPERTY",
            "element": type("Element", (), {
                "display_property_is_editable": True,
                "display_property_type": "FLOAT",
                "reset_display_property_to_default": lambda _self: resets.append(True),
            })(),
        })()
        event = types.SimpleNamespace(
            type="BACK_SPACE",
            value="PRESS",
            point=(10.0, 10.0),
        )

        self.assertEqual(
            menu.modal(FakeContext(window), event),
            {'PASS_THROUGH'},
        )
        self.assertEqual(resets, [])

    def test_escape_closes_only_the_topmost_menu(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._close_menu_enum_dropdown = lambda: False
        closes = []
        menu._begin_menu_close = lambda: closes.append(True)
        event = types.SimpleNamespace(type='ESC', value='PRESS')

        menu._menu_is_topmost = lambda: False
        self.assertEqual(
            menu.modal(FakeContext(window), event),
            {'PASS_THROUGH'},
        )
        self.assertFalse(closes)

        menu._menu_is_topmost = lambda: True
        self.assertEqual(
            menu.modal(FakeContext(window), event),
            {'RUNNING_MODAL'},
        )
        self.assertEqual(closes, [True])

    def test_wheel_over_numeric_row_changes_value_without_zooming_editor(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._ensure_layout = lambda **_kwargs: None
        menu._update_menu_hover = lambda _event: False
        menu._menu_mouse = lambda event: event.point
        menu._menu_contains = lambda _point: True
        calls = []
        row = type("Row", (), {
            "enabled": True,
            "kind": "PROPERTY",
            "element": type("Element", (), {
                "display_property_is_editable": True,
                "display_property_type": "FLOAT",
                "apply_property_wheel": lambda _self, direction, precise=False: (
                    calls.append((direction, precise)) or True
                ),
            })(),
        })()
        menu._menu_hovered_row = row
        menu._menu_mark_context_changed = lambda: calls.append("redraw")
        event = type("Event", (), {
            "type": "WHEELUPMOUSE",
            "value": "PRESS",
            "shift": True,
            "point": (10.0, 10.0),
        })()

        result = menu.modal(FakeContext(window), event)

        self.assertEqual(result, {'RUNNING_MODAL'})
        self.assertEqual(calls, [(1, True), "redraw"])

    def test_backspace_resets_hovered_boolean_row_without_leaking(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._ensure_layout = lambda **_kwargs: None
        menu._update_menu_hover = lambda _event: False
        calls = []
        row = type("Row", (), {
            "enabled": True,
            "kind": "PROPERTY",
            "element": type("Element", (), {
                "display_property_is_editable": True,
                "display_property_type": "BOOLEAN",
                "reset_display_property_to_default": lambda _self: (
                    calls.append("reset") or True
                ),
            })(),
        })()
        menu._menu_hovered_row = row
        menu._menu_mark_context_changed = lambda: calls.append("redraw")
        event = types.SimpleNamespace(type="BACK_SPACE", value="PRESS")

        result = menu.modal(FakeContext(window), event)

        self.assertEqual(result, {'RUNNING_MODAL'})
        self.assertEqual(calls, ["reset", "redraw"])

    def test_backspace_ignores_hovered_enum_row(self):
        menu = self.make_menu()
        window = FakeWindow([menu])
        menu._menu_close_requested = False
        menu._menu_closing_at = 0.0
        menu._menu_external_modal_active = False
        menu._area_is_live = lambda: True
        menu._has_external_modal = lambda _context: False
        menu._ensure_layout = lambda **_kwargs: None
        menu._update_menu_hover = lambda _event: False
        row = type("Row", (), {
            "enabled": True,
            "kind": "PROPERTY",
            "element": type("Element", (), {
                "display_property_is_editable": True,
                "display_property_type": "ENUM",
            })(),
        })()
        menu._menu_hovered_row = row
        event = types.SimpleNamespace(type="BACK_SPACE", value="PRESS")

        self.assertEqual(
            menu.modal(FakeContext(window), event),
            {'PASS_THROUGH'},
        )


if __name__ == "__main__":
    unittest.main()
