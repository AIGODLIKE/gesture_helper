from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "gesture_input.py"
PACKAGE = "_gesture_property_drag_test"


class Vector:
    def __init__(self, values):
        self.x, self.y = values

    def __sub__(self, other):
        return Vector((self.x - other.x, self.y - other.y))

    @property
    def length(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def copy(self):
        return Vector((self.x, self.y))


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_gesture_input_module():
    package = _module(PACKAGE)
    package.__path__ = [str(MODULE_PATH.parents[1])]
    gesture_package = _module(f"{PACKAGE}.gesture")
    gesture_package.__path__ = [str(MODULE_PATH.parent)]

    _module(
        f"{PACKAGE}.gesture.gesture_session",
        GestureSession=type("GestureSession", (), {}),
        InputSnapshot=type("InputSnapshot", (), {}),
        threshold_zone_from_distance=lambda *_args: None,
    )

    old_bpy = sys.modules.get("bpy")
    old_mathutils = sys.modules.get("mathutils")
    _module(
        "bpy",
        context=types.SimpleNamespace(),
        app=types.SimpleNamespace(timers=types.SimpleNamespace()),
    )
    _module("mathutils", Vector=Vector)

    name = f"{PACKAGE}.gesture.gesture_input"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        if old_bpy is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = old_bpy
        if old_mathutils is None:
            sys.modules.pop("mathutils", None)
        else:
            sys.modules["mathutils"] = old_mathutils
    return module


gesture_input = _load_gesture_input_module()


class FakeElement:
    def __init__(self, *, changed: bool, property_type="FLOAT", editable=True):
        self.changed = changed
        self.display_property_type = property_type
        self.display_property_is_editable = editable
        self.apply_calls = []
        self.wheel_calls = []
        self.restore_calls = []

    def property_drag_delta(self, start_mouse, mouse):
        return mouse.x - start_mouse.x

    def apply_property_drag(self, start_value, delta, *, precise=False):
        self.apply_calls.append((start_value, delta, precise))
        return self.changed

    def set_display_property_value(self, value):
        self.restore_calls.append(value)
        return self.changed

    def apply_property_wheel(self, direction, *, precise=False):
        self.wheel_calls.append((direction, precise))
        return self.changed


def _session(element, *, invoke_event_type="SPACE", moved=False):
    return types.SimpleNamespace(
        property_drag=(element, Vector((2.0, 3.0)), 10),
        invoke_event_type=invoke_event_type,
        _event_consumed=False,
        _poll_context_revision=4,
        _property_drag_moved=moved,
        _suppress_property_execute=False,
    )


def _event(event_type, value="NOTHING", *, x=8.0, y=9.0, shift=False):
    return types.SimpleNamespace(
        type=event_type,
        value=value,
        mouse_x=x,
        mouse_y=y,
        shift=shift,
    )


class GesturePropertyDragTests(unittest.TestCase):
    def setUp(self):
        self.processor = gesture_input.GestureInputProcessor()
        self.ops = object()

    def test_direction_context_uses_stable_rna_pointer_for_root_gesture(self):
        class Proxy:
            def as_pointer(self):
                return 42

        session = types.SimpleNamespace(
            trajectory_tree=types.SimpleNamespace(
                __len__=lambda _self: 0,
                last_element=None,
            ),
        )
        # SimpleNamespace special methods are resolved on the type, so use a
        # tiny concrete tree for len().
        class EmptyTree:
            last_element = None

            def __len__(self):
                return 0

        session.trajectory_tree = EmptyTree()

        first = gesture_input.direction_items_context_id(session, Proxy())
        second = gesture_input.direction_items_context_id(session, Proxy())

        self.assertEqual(first, 42)
        self.assertEqual(second, first)

    def test_direction_context_uses_stable_rna_pointer_for_child(self):
        class Proxy:
            def as_pointer(self):
                return 84

        class ChildTree:
            last_element = Proxy()

            def __len__(self):
                return 1

        session = types.SimpleNamespace(trajectory_tree=ChildTree())

        self.assertEqual(
            gesture_input.direction_items_context_id(session, object()),
            84,
        )

    def test_gesture_redraw_never_falls_back_to_the_whole_area(self):
        class FakeArea:
            regions = ()

            def __init__(self):
                self.redraws = 0

            def tag_redraw(self):
                self.redraws += 1

        area = FakeArea()
        session = types.SimpleNamespace(area=area, screen=None)

        gesture_input.tag_redraw_gesture_screen(session)

        self.assertEqual(area.redraws, 0)

    def test_screen_fallback_redraws_window_regions_only(self):
        class FakeRegion:
            def __init__(self, region_type):
                self.type = region_type
                self.redraws = 0

            def tag_redraw(self):
                self.redraws += 1

        window = FakeRegion("WINDOW")
        sidebar = FakeRegion("UI")
        area = types.SimpleNamespace(regions=(sidebar, window))
        session = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(areas=(area,)),
        )

        gesture_input.tag_redraw_gesture_screen(session)

        self.assertEqual(window.redraws, 1)
        self.assertEqual(sidebar.redraws, 0)

    def test_unchanged_mousemove_is_consumed_without_refresh(self):
        element = FakeElement(changed=False)
        session = _session(element)

        with patch.object(gesture_input, "refresh_snapshot") as refresh:
            result = self.processor._handle_property_drag(
                session,
                self.ops,
                _event("MOUSEMOVE"),
            )

        self.assertIs(result, False)
        self.assertTrue(session._event_consumed)
        self.assertEqual(session._poll_context_revision, 4)
        self.assertEqual(element.apply_calls, [(10, 6.0, False)])
        refresh.assert_not_called()

    def test_changed_mousemove_increments_revision_and_refreshes(self):
        element = FakeElement(changed=True)
        session = _session(element)

        with patch.object(gesture_input, "refresh_snapshot") as refresh:
            result = self.processor._handle_property_drag(
                session,
                self.ops,
                _event("MOUSEMOVE", shift=True),
            )

        self.assertIs(result, True)
        self.assertTrue(session._event_consumed)
        self.assertEqual(session._poll_context_revision, 5)
        self.assertEqual(element.apply_calls, [(10, 6.0, True)])
        refresh.assert_called_once_with(session, self.ops)

    def test_lmb_invoke_release_is_not_consumed_and_can_exit(self):
        element = FakeElement(changed=True)
        session = _session(
            element,
            invoke_event_type="LEFTMOUSE",
            moved=True,
        )

        result = self.processor._handle_property_drag(
            session,
            self.ops,
            _event("LEFTMOUSE", "RELEASE"),
        )

        self.assertIsNone(result)
        self.assertFalse(session._event_consumed)
        self.assertIsNone(session.property_drag)
        self.assertTrue(session._suppress_property_execute)
        self.assertFalse(session._property_drag_moved)
        self.assertEqual(element.apply_calls, [])

    def test_wheel_up_changes_hovered_numeric_property(self):
        element = FakeElement(changed=True, property_type="FLOAT")
        session = _session(element)
        session.property_drag = None

        with patch.object(self.processor, "_hovered_property_row", return_value=element), \
                patch.object(gesture_input, "refresh_snapshot") as refresh:
            result = self.processor._handle_property_wheel(
                session,
                self.ops,
                _event("WHEELUPMOUSE", "PRESS", shift=True),
            )

        self.assertIs(result, True)
        self.assertTrue(session._event_consumed)
        self.assertTrue(session._suppress_property_execute)
        self.assertEqual(session._poll_context_revision, 5)
        self.assertEqual(element.wheel_calls, [(1, True)])
        refresh.assert_called_once_with(session, self.ops)

    def test_wheel_down_noop_is_still_consumed(self):
        element = FakeElement(changed=False, property_type="INT")
        session = _session(element)
        session.property_drag = None

        with patch.object(self.processor, "_hovered_property_row", return_value=element), \
                patch.object(gesture_input, "refresh_snapshot") as refresh:
            result = self.processor._handle_property_wheel(
                session,
                self.ops,
                _event("WHEELDOWNMOUSE", "PRESS"),
            )

        self.assertIs(result, False)
        self.assertTrue(session._event_consumed)
        self.assertTrue(session._suppress_property_execute)
        self.assertEqual(session._poll_context_revision, 4)
        self.assertEqual(element.wheel_calls, [(-1, False)])
        refresh.assert_not_called()

    def test_wheel_ignores_non_numeric_or_uneditable_rows(self):
        for element in (
                FakeElement(changed=True, property_type="BOOLEAN"),
                FakeElement(changed=True, property_type="FLOAT", editable=False),
        ):
            session = _session(element)
            session.property_drag = None
            with patch.object(self.processor, "_hovered_property_row", return_value=element):
                result = self.processor._handle_property_wheel(
                    session,
                    self.ops,
                    _event("WHEELUPMOUSE", "PRESS"),
                )
            self.assertIsNone(result)
            self.assertFalse(session._event_consumed)
            self.assertEqual(element.wheel_calls, [])

    def test_wheel_is_swallowed_while_dragging(self):
        element = FakeElement(changed=True)
        session = _session(element)

        result = self.processor._handle_property_drag(
            session,
            self.ops,
            _event("WHEELUPMOUSE", "PRESS"),
        )

        self.assertIs(result, False)
        self.assertTrue(session._event_consumed)
        self.assertEqual(element.wheel_calls, [])

    def test_cancel_property_drag_restores_once(self):
        element = FakeElement(changed=True)
        session = _session(element, moved=True)

        self.assertTrue(
            self.processor.cancel_property_drag(session, self.ops),
        )
        self.assertEqual(element.restore_calls, [10])
        self.assertIsNone(session.property_drag)
        self.assertFalse(session._property_drag_moved)

        self.assertFalse(
            self.processor.cancel_property_drag(session, self.ops),
        )
        self.assertEqual(element.restore_calls, [10])

    def test_error_item_click_requests_repair_only_inside_visible_item(self):
        element = types.SimpleNamespace(
            item_draw_area=(0.0, 0.0, 20.0, 20.0),
            extension_by_child_draw_area=None,
            is_layout_container=False,
        )
        session = types.SimpleNamespace(
            property_drag=None,
            repair_element=None,
            _event_consumed=False,
        )
        element_package = types.ModuleType(f"{PACKAGE}.element")
        element_package.__path__ = []
        extension_hit = types.ModuleType(f"{PACKAGE}.element.extension_hit")
        extension_hit._mouse_for = lambda _element, _ops: (10.0, 10.0)
        extension_hit.point_in_rect = lambda point, rect: (
            rect is not None
            and rect[0] < point[0] < rect[2]
            and rect[1] < point[1] < rect[3]
        )
        element_status = types.ModuleType(f"{PACKAGE}.element.element_status")
        element_status.get_element_status_info = lambda _element, ops=None: (
            types.SimpleNamespace(status=types.SimpleNamespace(is_error=True))
        )

        with patch.dict(sys.modules, {
            element_package.__name__: element_package,
            extension_hit.__name__: extension_hit,
            element_status.__name__: element_status,
        }), patch.object(
            gesture_input,
            "get_runtime_hovered_element",
            return_value=element,
        ):
            handled = self.processor._handle_repair_click(
                session,
                self.ops,
                _event("LEFTMOUSE", "PRESS"),
            )

        self.assertTrue(handled)
        self.assertIs(session.repair_element, element)
        self.assertTrue(session._event_consumed)

    def test_warning_item_click_does_not_request_repair(self):
        element = types.SimpleNamespace(
            item_draw_area=(0.0, 0.0, 20.0, 20.0),
            extension_by_child_draw_area=None,
            is_layout_container=False,
        )
        session = types.SimpleNamespace(
            property_drag=None,
            repair_element=None,
            _event_consumed=False,
        )
        element_package = types.ModuleType(f"{PACKAGE}.element")
        element_package.__path__ = []
        extension_hit = types.ModuleType(f"{PACKAGE}.element.extension_hit")
        extension_hit._mouse_for = lambda _element, _ops: (10.0, 10.0)
        extension_hit.point_in_rect = lambda point, rect: rect is not None
        element_status = types.ModuleType(f"{PACKAGE}.element.element_status")
        element_status.get_element_status_info = lambda _element, ops=None: (
            types.SimpleNamespace(status=types.SimpleNamespace(is_error=False))
        )

        with patch.dict(sys.modules, {
            element_package.__name__: element_package,
            extension_hit.__name__: extension_hit,
            element_status.__name__: element_status,
        }), patch.object(
            gesture_input,
            "get_runtime_hovered_element",
            return_value=element,
        ):
            handled = self.processor._handle_repair_click(
                session,
                self.ops,
                _event("LEFTMOUSE", "PRESS"),
            )

        self.assertFalse(handled)
        self.assertIsNone(session.repair_element)
        self.assertFalse(session._event_consumed)

    def test_visual_trail_is_sampled_and_bounded(self):
        session = types.SimpleNamespace(
            trajectory_mouse_move=[],
            trajectory_mouse_move_time=[],
        )

        self.assertTrue(
            gesture_input.append_visual_trail_point(session, Vector((0.0, 0.0)))
        )
        self.assertFalse(
            gesture_input.append_visual_trail_point(session, Vector((1.0, 0.0)))
        )
        for index in range(1, 400):
            gesture_input.append_visual_trail_point(
                session,
                Vector((index * 3.0, 0.0)),
            )

        self.assertLessEqual(
            len(session.trajectory_mouse_move),
            gesture_input._VISUAL_TRAIL_MAX_POINTS,
        )
        self.assertEqual(
            len(session.trajectory_mouse_move),
            len(session.trajectory_mouse_move_time),
        )
        self.assertEqual(session.trajectory_mouse_move[0].x, 0.0)
        self.assertEqual(session.trajectory_mouse_move[-1].x, 399 * 3.0)


if __name__ == "__main__":
    unittest.main()
