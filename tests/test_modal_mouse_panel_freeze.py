from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).parents[1] / "ops" / "modal_mouse.py"
PACKAGE = "_gesture_modal_mouse_test"


class Vector:
    def __init__(self, values):
        self.x, self.y = values

    def copy(self):
        return Vector((self.x, self.y))


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


package = _module(PACKAGE)
package.__path__ = [str(MODULE_PATH.parents[1])]
ops_package = _module(f"{PACKAGE}.ops")
ops_package.__path__ = [str(MODULE_PATH.parent)]
utils_package = _module(f"{PACKAGE}.utils")
utils_package.__path__ = [str(MODULE_PATH.parents[1] / "utils")]


class FakeMouseModal:
    def start_mouse(self, event):
        self.mouse = Vector((event.mouse_x, event.mouse_y))

    def value_delta(self, event, _value_mode):
        return event.delta

    def set_cursor(self, _context, _value_mode):
        return None

    def exit(self):
        return None


class FakePublicGpu:
    pass


def _property(**_kwargs):
    return None


bpy = _module("bpy")
bpy.context = types.SimpleNamespace()
bpy.types = types.SimpleNamespace(
    Operator=type("Operator", (), {}),
    SpaceView3D=type("SpaceView3D", (), {}),
)
bpy_props = _module(
    "bpy.props",
    BoolProperty=_property,
    EnumProperty=_property,
    StringProperty=_property,
)
bpy.props = bpy_props
bpy_app = _module("bpy.app")
bpy_translations = _module("bpy.app.translations", pgettext=lambda text: text)
bpy_app.translations = bpy_translations
bpy.app = bpy_app

_module("gpu", state=types.SimpleNamespace())
_module("mathutils", Vector=Vector)
bl_operators = _module("bl_operators")
bl_operators.__path__ = []
_module(
    "bl_operators.wm",
    operator_value_undo_return=lambda _value: {"FINISHED"},
)
_module(
    f"{PACKAGE}.utils.enum",
    ENUM_NUMBER_VALUE_CHANGE_MODE=("HEADER", "X", "Y"),
)
_module(
    f"{PACKAGE}.utils.public",
    by_path_set_value=lambda *_args: None,
    PublicMouseModal=FakeMouseModal,
    debug_print=lambda *_args, **_kwargs: None,
    poll_addon_preferences=lambda _cls: True,
)
_module(
    f"{PACKAGE}.utils.expression",
    resolve_context_path=lambda *_args: None,
)
_module(f"{PACKAGE}.utils.public_gpu", PublicGpu=FakePublicGpu)

freeze_calls = []
_module(
    f"{PACKAGE}.utils.ui_draw_sync",
    begin_panel_layout_freeze=lambda owner: freeze_calls.append(("begin", owner)),
    cancel_all=lambda: freeze_calls.append(("cancel_all", None)),
    end_panel_layout_freeze=lambda owner: freeze_calls.append(("end", owner)),
    tag_gesture_ui_regions=lambda: freeze_calls.append(("tag_ui", None)),
)

name = f"{PACKAGE}.ops.modal_mouse"
spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
modal_mouse = importlib.util.module_from_spec(spec)
sys.modules[name] = modal_mouse
assert spec.loader is not None
spec.loader.exec_module(modal_mouse)


class FakeRegion:
    def __init__(self):
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class FakeArea:
    type = "VIEW_3D"

    def __init__(self, region=None):
        self.region = region
        self.redraws = 0
        self.header = None

    def tag_redraw(self):
        self.redraws += 1

    def header_text_set(self, text):
        self.header = text


def _event(event_type, value="PRESS", *, delta=0.0):
    return types.SimpleNamespace(
        type=event_type,
        value=value,
        mouse_x=10,
        mouse_y=20,
        mouse_region_x=10,
        mouse_region_y=20,
        delta=delta,
    )


class ModalMousePanelFreezeTests(unittest.TestCase):
    def setUp(self):
        freeze_calls.clear()

    def test_overlay_redraw_targets_only_the_window_region(self):
        region = FakeRegion()
        area = FakeArea(region)
        _module(
            f"{PACKAGE}.utils.region_mouse",
            find_window_region=lambda candidate: candidate.region,
        )
        operator = modal_mouse.ModalMouseOperator()
        operator._modal_area = area

        operator._tag_window_redraw()

        self.assertEqual(region.redraws, 1)
        self.assertEqual(area.redraws, 0)

    def test_overlay_redraw_skips_whole_area_fallback(self):
        area = FakeArea(region=None)
        _module(
            f"{PACKAGE}.utils.region_mouse",
            find_window_region=lambda _candidate: None,
        )
        operator = modal_mouse.ModalMouseOperator()
        operator._modal_area = area

        operator._tag_window_redraw()

        self.assertEqual(area.redraws, 0)

    def test_unchanged_display_text_does_not_reset_area_header(self):
        region = FakeRegion()
        area = FakeArea(region)
        area.header_text_set = Mock(wraps=area.header_text_set)
        context = types.SimpleNamespace(area=area)
        _module(
            f"{PACKAGE}.utils.region_mouse",
            find_window_region=lambda candidate: candidate.region,
        )
        operator = modal_mouse.ModalMouseOperator()
        operator._display_text = ""

        operator._set_display_text(context, "Value 10", mouse=Vector((10, 20)))
        operator._set_display_text(context, "Value 10", mouse=Vector((20, 30)))

        area.header_text_set.assert_called_once_with("Value 10")
        self.assertEqual(region.redraws, 2)

    def test_unchanged_integer_drag_does_not_write_rna(self):
        state = {"value": 10}
        writes = []

        def resolve(*_args):
            return state["value"]

        def write(_context, _path, value):
            writes.append(value)
            state["value"] = value

        modal_mouse.resolve_context_path = resolve
        modal_mouse.by_path_set_value = write
        modal_mouse.bpy.context = object()
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.value_mode = "X"
        operator.invert = False
        operator.data_path = "scene.value"
        operator.header_text = "Value %d"
        operator._set_display_text = Mock()

        result = operator.modal(types.SimpleNamespace(), _event("MOUSEMOVE", delta=0.2))

        self.assertEqual(result, {"RUNNING_MODAL"})
        self.assertEqual(writes, [])
        operator._set_display_text.assert_called_once()

    def test_changed_drag_writes_once(self):
        state = {"value": 10}
        writes = []

        def resolve(*_args):
            return state["value"]

        def write(_context, _path, value):
            writes.append(value)
            state["value"] = value

        modal_mouse.resolve_context_path = resolve
        modal_mouse.by_path_set_value = write
        modal_mouse.bpy.context = object()
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.value_mode = "X"
        operator.invert = False
        operator.data_path = "scene.value"
        operator.header_text = "Value %d"
        operator._set_display_text = Mock()

        operator.modal(types.SimpleNamespace(), _event("MOUSEMOVE", delta=2.0))

        self.assertEqual(writes, [12])

    def test_invoke_and_exit_bracket_the_explicit_panel_freeze(self):
        modal_mouse.resolve_context_path = lambda *_args: 10
        region = FakeRegion()
        area = FakeArea(region)
        window_manager = types.SimpleNamespace(modal_handler_add=Mock())
        window = types.SimpleNamespace(
            cursor_modal_set=Mock(),
            cursor_modal_restore=Mock(),
        )
        context = types.SimpleNamespace(
            area=area,
            window=window,
            window_manager=window_manager,
        )
        operator = modal_mouse.ModalMouseOperator()
        operator.data_path = "scene.value"
        operator.header_text = "Value %d"
        operator.value_mode = "X"
        operator.register_draw = Mock()
        operator.unregister_draw = Mock()

        result = operator.invoke(context, _event("LEFTMOUSE"))

        self.assertEqual(result, {"RUNNING_MODAL"})
        self.assertEqual(
            [entry[0] for entry in freeze_calls],
            ["cancel_all", "begin", "tag_ui"],
        )
        window_manager.modal_handler_add.assert_called_once_with(operator)
        window.cursor_modal_set.assert_called_once_with("NONE")

        operator.exit()

        self.assertEqual(
            [entry[0] for entry in freeze_calls],
            ["cancel_all", "begin", "tag_ui", "end", "tag_ui"],
        )
        window.cursor_modal_restore.assert_called_once_with()

    def test_lmb_started_modal_confirms_and_restores_cursor_on_release(self):
        modal_mouse.resolve_context_path = lambda *_args: 10
        area = FakeArea(FakeRegion())
        window = types.SimpleNamespace(
            cursor_modal_set=Mock(),
            cursor_modal_restore=Mock(),
        )
        context = types.SimpleNamespace(
            area=area,
            window=window,
            window_manager=types.SimpleNamespace(modal_handler_add=Mock()),
        )
        operator = modal_mouse.ModalMouseOperator()
        operator.data_path = "scene.value"
        operator.header_text = "Value %d"
        operator.value_mode = "X"
        operator.register_draw = Mock()
        operator.unregister_draw = Mock()

        self.assertEqual(
            operator.invoke(context, _event("LEFTMOUSE", "PRESS")),
            {"RUNNING_MODAL"},
        )
        self.assertEqual(
            operator.modal(context, _event("LEFTMOUSE", "RELEASE")),
            {"FINISHED"},
        )
        window.cursor_modal_set.assert_called_once_with("NONE")
        window.cursor_modal_restore.assert_called_once_with()

    def test_window_deactivate_restores_and_releases_modal(self):
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.value_mode = "X"
        operator.__restore__ = Mock()
        operator.exit = Mock()
        operator.set_cursor = Mock()

        class DeactivateEvent:
            type = "WINDOW_DEACTIVATE"

            @property
            def mouse_region_x(self):
                raise AssertionError("deactivation must not read mouse_region_x")

            @property
            def mouse_region_y(self):
                raise AssertionError("deactivation must not read mouse_region_y")

        result = operator.modal(types.SimpleNamespace(), DeactivateEvent())

        self.assertEqual(result, {"CANCELLED"})
        operator.__restore__.assert_called_once_with()
        operator.exit.assert_called_once_with()
        operator.set_cursor.assert_not_called()

    def test_restore_error_still_releases_explicit_panel_freeze(self):
        area = FakeArea(FakeRegion())
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator._modal_area = area
        operator._panel_freeze_active = True
        operator.__restore__ = Mock(side_effect=RuntimeError("target disappeared"))
        operator.unregister_draw = Mock()

        with self.assertRaisesRegex(RuntimeError, "target disappeared"):
            operator.modal(types.SimpleNamespace(), _event("WINDOW_DEACTIVATE"))

        operator.unregister_draw.assert_called_once_with()
        self.assertEqual(
            [entry[0] for entry in freeze_calls],
            ["end", "tag_ui"],
        )
        self.assertFalse(operator._panel_freeze_active)
        self.assertIsNone(operator._modal_area)

    def test_stale_release_events_do_not_finish_handoff_modal(self):
        for event_type in ("LEFTMOUSE", "RIGHTMOUSE", "ESC"):
            with self.subTest(event_type=event_type):
                operator = modal_mouse.ModalMouseOperator()
                operator.___value___ = 10
                operator.value_mode = "X"
                operator.__restore__ = Mock()
                operator.exit = Mock()

                result = operator.modal(
                    types.SimpleNamespace(),
                    _event(event_type, "RELEASE"),
                )

                self.assertEqual(result, {"RUNNING_MODAL"})
                operator.__restore__.assert_not_called()
                operator.exit.assert_not_called()

    def test_lmb_and_cancel_buttons_only_act_on_press(self):
        confirm = modal_mouse.ModalMouseOperator()
        confirm.___value___ = 10
        confirm.value_mode = "X"
        confirm.__restore__ = Mock()
        confirm.exit = Mock()

        self.assertEqual(
            confirm.modal(types.SimpleNamespace(), _event("LEFTMOUSE", "PRESS")),
            {"FINISHED"},
        )
        confirm.__restore__.assert_not_called()
        confirm.exit.assert_called_once_with()

        for event_type in ("RIGHTMOUSE", "ESC"):
            with self.subTest(event_type=event_type):
                cancel = modal_mouse.ModalMouseOperator()
                cancel.___value___ = 10
                cancel.value_mode = "X"
                cancel.__restore__ = Mock()
                cancel.exit = Mock()

                self.assertEqual(
                    cancel.modal(
                        types.SimpleNamespace(),
                        _event(event_type, "PRESS"),
                    ),
                    {"CANCELLED"},
                )
                cancel.__restore__.assert_called_once_with()
                cancel.exit.assert_called_once_with()

    def test_cancel_callback_exits_even_when_restore_raises(self):
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.__restore__ = Mock(side_effect=RuntimeError("restore failed"))
        operator.exit = Mock()

        with self.assertRaisesRegex(RuntimeError, "restore failed"):
            operator.cancel(types.SimpleNamespace())

        operator.exit.assert_called_once_with()

    def test_restore_error_is_preserved_when_exit_also_fails(self):
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        restore_error = RuntimeError("restore failed")
        operator.__restore__ = Mock(side_effect=restore_error)
        operator.exit = Mock(side_effect=RuntimeError("exit failed"))

        with self.assertRaises(RuntimeError) as raised:
            operator._cancel_and_exit()

        self.assertIs(raised.exception, restore_error)
        operator.exit.assert_called_once_with()

    def test_mousemove_error_restores_and_releases_explicit_freeze(self):
        area = FakeArea(FakeRegion())
        window = types.SimpleNamespace(cursor_modal_restore=Mock())
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.value_mode = "X"
        operator.invert = False
        operator.data_path = "scene.value"
        operator._modal_area = area
        operator._modal_window = window
        operator._panel_freeze_active = True
        operator._cursor_modal_active = True
        operator.unregister_draw = Mock()
        write_error = RuntimeError("RNA write failed")

        with (
                patch.object(modal_mouse, "resolve_context_path", return_value=10),
                patch.object(modal_mouse, "by_path_set_value", side_effect=write_error),
                self.assertRaises(RuntimeError) as raised,
        ):
            operator.modal(
                types.SimpleNamespace(),
                _event("MOUSEMOVE", delta=2.0),
            )

        self.assertIs(raised.exception, write_error)
        operator.unregister_draw.assert_called_once_with()
        self.assertEqual(
            [entry[0] for entry in freeze_calls],
            ["end", "tag_ui"],
        )
        self.assertFalse(operator._panel_freeze_active)
        self.assertIsNone(operator._modal_area)
        self.assertIsNone(operator._modal_window)
        window.cursor_modal_restore.assert_called_once_with()

    def test_post_write_resolve_error_restores_original_value(self):
        area = FakeArea(FakeRegion())
        window = types.SimpleNamespace(cursor_modal_restore=Mock())
        operator = modal_mouse.ModalMouseOperator()
        operator.___value___ = 10
        operator.value_mode = "X"
        operator.invert = False
        operator.data_path = "scene.value"
        operator._modal_area = area
        operator._modal_window = window
        operator._panel_freeze_active = True
        operator._cursor_modal_active = True
        operator.unregister_draw = Mock()
        state = {"value": 10}
        writes = []
        resolve_error = RuntimeError("post-write resolve failed")

        def resolve(*_args):
            if writes:
                raise resolve_error
            return state["value"]

        def write(_context, _path, value):
            writes.append(value)
            state["value"] = value

        with (
                patch.object(modal_mouse, "resolve_context_path", side_effect=resolve),
                patch.object(modal_mouse, "by_path_set_value", side_effect=write),
                self.assertRaises(RuntimeError) as raised,
        ):
            operator.modal(
                types.SimpleNamespace(),
                _event("MOUSEMOVE", delta=2.0),
            )

        self.assertIs(raised.exception, resolve_error)
        self.assertEqual(writes, [12, 10])
        self.assertEqual(state["value"], 10)
        self.assertFalse(operator._panel_freeze_active)
        self.assertIsNone(operator._modal_area)
        self.assertIsNone(operator._modal_window)
        window.cursor_modal_restore.assert_called_once_with()

    def test_draw_cleanup_error_still_releases_freeze_and_owner_context(self):
        area = FakeArea(FakeRegion())
        window = types.SimpleNamespace(cursor_modal_restore=Mock())
        operator = modal_mouse.ModalMouseOperator()
        operator._modal_area = area
        operator._modal_window = window
        operator._panel_freeze_active = True
        operator._cursor_modal_active = True
        operator.unregister_draw = Mock(side_effect=RuntimeError("draw handle failed"))

        with self.assertRaisesRegex(RuntimeError, "draw handle failed"):
            operator.exit()

        self.assertEqual(
            [entry[0] for entry in freeze_calls],
            ["end", "tag_ui"],
        )
        self.assertFalse(operator._panel_freeze_active)
        self.assertIsNone(operator._modal_area)
        self.assertIsNone(operator._modal_window)
        window.cursor_modal_restore.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
