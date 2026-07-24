from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "ops" / "gesture.py"
PACKAGE = "_gesture_modal_lifecycle_test"
TRACE: list[str] = []


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _Handoff:
    def __init__(self, needs_interface: bool = False):
        self.needs_interface = needs_interface


class _GestureSession:
    def __init__(self):
        self.modal_report_done = False
        self.property_drag = None
        self._suppress_property_execute = False
        self._event_consumed = False
        self.repair_element = None
        self.handoff = _Handoff()
        self.clear_handoff_calls = 0

    def clear_handoff(self):
        TRACE.append("clear_handoff")
        self.clear_handoff_calls += 1
        self.handoff = _Handoff()


class _GestureInputProcessor:
    def __init__(self):
        self.cancel_calls = 0
        self.on_event_calls = 0
        self.on_event_error = None
        self.dirty = False

    def cancel_property_drag(self, session, _ops, *, refresh=False):
        TRACE.append("cancel_property_drag")
        self.cancel_calls += 1
        drag = session.property_drag
        if drag is None:
            return False
        element, _start_mouse, start_value = drag
        session.property_drag = None
        return element.set_display_property_value(start_value)

    def on_event(self, _session, _ops, _event):
        self.on_event_calls += 1
        if self.on_event_error is not None:
            raise self.on_event_error
        return self.dirty


class _GestureExecutor:
    def __init__(self):
        self.immediate_calls = 0
        self.immediate_error = None
        self.immediate_result = False

    def try_immediate_implementation(self, _session, _ops):
        self.immediate_calls += 1
        if self.immediate_error is not None:
            raise self.immediate_error
        return self.immediate_result


class _PublicOperator:
    pass


class _GestureHandle:
    def _cancel_gesture_timeout_timer(self):
        TRACE.append("cancel_timeout")
        self.timeout_cancel_calls += 1

    def _tag_redraw_gesture_screen(self):
        self.redraw_calls += 1


class _GestureGpuDraw:
    __finishing_draw_instances__ = {}

    def unregister_draw(self):
        TRACE.append("unregister_draw")
        self.unregister_draw_calls += 1
        error = getattr(self, "unregister_draw_error", None)
        if error is not None:
            raise error


class _GestureRuntimeMixin:
    def init_modal(self, _event):
        self.init_modal_calls += 1


class _GesturePassThroughKeymap:
    pass


def _property(**_kwargs):
    return None


def _load_gesture_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    ops_package = _module(f"{PACKAGE}.ops")
    ops_package.__path__ = [str(MODULE_PATH.parent)]
    gesture_package = _module(f"{PACKAGE}.gesture")
    gesture_package.__path__ = [str(MODULE_PATH.parents[1] / "gesture")]
    utils_package = _module(f"{PACKAGE}.utils")
    utils_package.__path__ = [str(MODULE_PATH.parents[1] / "utils")]

    old_modules = {
        name: sys.modules.get(name)
        for name in ("bpy", "bpy.app", "bpy.app.translations", "bpy.props")
    }
    bpy = _module("bpy")
    bpy.__path__ = []
    bpy.context = types.SimpleNamespace(region=None)
    bpy.types = types.SimpleNamespace(Context=object, Event=object)
    bpy_app = _module("bpy.app")
    bpy_app.__path__ = []
    translations = _module(
        "bpy.app.translations",
        pgettext_iface=lambda text: text,
    )
    bpy_props = _module("bpy.props", StringProperty=_property)
    bpy.app = bpy_app
    bpy.props = bpy_props
    bpy_app.translations = translations

    _module(
        f"{PACKAGE}.gesture.gesture_draw_gpu",
        GestureGpuDraw=_GestureGpuDraw,
    )
    _module(
        f"{PACKAGE}.gesture.gesture_executor",
        GestureExecutor=_GestureExecutor,
    )
    _module(
        f"{PACKAGE}.gesture.gesture_handle",
        GestureHandle=_GestureHandle,
    )
    gesture_input = _module(
        f"{PACKAGE}.gesture.gesture_input",
        GestureInputProcessor=_GestureInputProcessor,
        ensure_trajectory_seed=lambda *_args: None,
        refresh_snapshot=lambda *_args: None,
        schedule_timeout_timer=lambda *_args: None,
        clear_gesture_item_memos=(
            lambda *_args: TRACE.append("clear_memos")
        ),
    )
    _module(
        f"{PACKAGE}.gesture.gesture_runtime",
        GestureRuntimeMixin=_GestureRuntimeMixin,
    )
    _module(
        f"{PACKAGE}.gesture.gesture_session",
        GestureSession=_GestureSession,
    )
    _module(
        f"{PACKAGE}.gesture.pass_through",
        GesturePassThroughKeymap=_GesturePassThroughKeymap,
        cancel_deferred_operator_timers=(
            lambda: TRACE.append("cancel_deferred")
        ),
    )
    _module(
        f"{PACKAGE}.utils.adapter",
        operator_setattr=setattr,
    )
    _module(
        f"{PACKAGE}.utils.public",
        PublicOperator=_PublicOperator,
        debug_print=lambda *_args, **_kwargs: None,
    )
    _module(
        f"{PACKAGE}.utils.ui_draw_sync",
        cancel_modal_ui_refresh=lambda: TRACE.append("cancel_ui_refresh"),
        tag_gesture_ui_regions=lambda: TRACE.append("tag_ui"),
    )

    name = f"{PACKAGE}.ops.gesture"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        for module_name, old_module in old_modules.items():
            if old_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = old_module
    return module, gesture_input


gesture, _gesture_input = _load_gesture_module()


class _PropertyElement:
    def __init__(self):
        self.restored_values = []

    def set_display_property_value(self, value):
        TRACE.append("restore_property")
        self.restored_values.append(value)
        return True


def _event(event_type: str, value: str = "PRESS"):
    return types.SimpleNamespace(
        type=event_type,
        value=value,
        type_prev="NONE",
        value_prev="NOTHING",
    )


class GestureModalLifecycleTests(unittest.TestCase):
    def setUp(self):
        TRACE.clear()

    def _operator_with_scrub(self):
        operator = gesture.GestureOperator()
        operator.unregister_draw_calls = 0
        operator.timeout_cancel_calls = 0
        operator.redraw_calls = 0
        operator.init_modal_calls = 0
        operator.is_exit = False
        element = _PropertyElement()
        operator.session.property_drag = (element, object(), 37)
        operator.session._suppress_property_execute = True
        operator.session.repair_element = object()
        operator.session.handoff = _Handoff(needs_interface=True)
        return operator, element

    def _assert_cancelled(self, operator, element):
        self.assertTrue(operator.session.modal_report_done)
        self.assertTrue(operator._modal_cleaned)
        self.assertTrue(operator._modal_cancelled)
        self.assertIsNone(operator.session.property_drag)
        self.assertEqual(element.restored_values, [37])
        self.assertFalse(operator.session._suppress_property_execute)
        self.assertIsNone(operator.session.repair_element)
        self.assertFalse(operator.session.handoff.needs_interface)
        self.assertEqual(operator.session.clear_handoff_calls, 1)
        self.assertEqual(operator._input.cancel_calls, 1)
        self.assertEqual(operator.unregister_draw_calls, 1)
        self.assertEqual(operator.timeout_cancel_calls, 1)
        self.assertEqual(
            TRACE,
            [
                "cancel_property_drag",
                "restore_property",
                "clear_handoff",
                "unregister_draw",
                "cancel_ui_refresh",
                "cancel_timeout",
                "clear_memos",
            ],
        )

    def test_escape_and_right_mouse_press_share_cancel_path(self):
        for event_type in ("ESC", "RIGHTMOUSE"):
            with self.subTest(event_type=event_type):
                TRACE.clear()
                operator, element = self._operator_with_scrub()

                result = operator.modal(object(), _event(event_type))

                self.assertEqual(result, {"CANCELLED"})
                self.assertEqual(operator._input.on_event_calls, 0)
                self.assertEqual(operator._executor.immediate_calls, 0)
                self._assert_cancelled(operator, element)

    def test_window_deactivate_uses_cancel_path(self):
        operator, element = self._operator_with_scrub()

        result = operator.modal(object(), _event("WINDOW_DEACTIVATE", "NOTHING"))

        self.assertEqual(result, {"CANCELLED"})
        self._assert_cancelled(operator, element)

    def test_blender_cancel_is_idempotent(self):
        operator, element = self._operator_with_scrub()

        operator.cancel(object())
        operator.cancel(object())

        self._assert_cancelled(operator, element)

    def test_cancel_after_successful_cleanup_keeps_valid_handoff(self):
        operator, _element = self._operator_with_scrub()
        operator._modal_cleaned = True
        operator.session.property_drag = None

        operator.cancel(object())

        self.assertFalse(operator._modal_cancelled)
        self.assertTrue(operator.session.handoff.needs_interface)
        self.assertEqual(TRACE, [])

    def test_draw_cleanup_error_still_cancels_ui_refresh_and_timeout(self):
        operator, _element = self._operator_with_scrub()
        original = RuntimeError("draw cleanup failed")
        operator.unregister_draw_error = original

        with self.assertRaises(RuntimeError) as raised:
            operator.__exit_modal__()

        self.assertIs(raised.exception, original)
        self.assertTrue(operator._modal_cleaned)
        self.assertEqual(operator.unregister_draw_calls, 1)
        self.assertEqual(operator.timeout_cancel_calls, 1)
        self.assertEqual(
            TRACE,
            ["unregister_draw", "cancel_ui_refresh", "cancel_timeout"],
        )

    def test_release_does_not_trigger_explicit_cancel(self):
        operator, _element = self._operator_with_scrub()
        operator.session.property_drag = None
        operator.session.repair_element = None
        operator.session._suppress_property_execute = False

        result = operator.modal(object(), _event("ESC", "RELEASE"))

        self.assertEqual(result, {"RUNNING_MODAL"})
        self.assertFalse(operator._modal_cancelled)
        self.assertEqual(operator._input.on_event_calls, 1)
        self.assertEqual(operator._executor.immediate_calls, 1)
        self.assertEqual(TRACE, [])

    def test_on_event_error_cleans_up_and_preserves_original_exception(self):
        operator, element = self._operator_with_scrub()
        original = RuntimeError("input failed")
        operator._input.on_event_error = original

        with self.assertRaises(RuntimeError) as raised:
            operator.modal(object(), _event("MOUSEMOVE"))

        self.assertIs(raised.exception, original)
        self.assertEqual(operator._executor.immediate_calls, 0)
        self._assert_cancelled(operator, element)

    def test_immediate_error_cleans_up_and_preserves_original_exception(self):
        operator, element = self._operator_with_scrub()
        operator.session.repair_element = None
        original = LookupError("immediate failed")
        operator._executor.immediate_error = original

        with self.assertRaises(LookupError) as raised:
            operator.modal(object(), _event("MOUSEMOVE"))

        self.assertIs(raised.exception, original)
        self.assertEqual(operator._input.on_event_calls, 1)
        self.assertEqual(operator._executor.immediate_calls, 1)
        self._assert_cancelled(operator, element)


if __name__ == "__main__":
    unittest.main()
