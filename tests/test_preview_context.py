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
    bpy.types = types.SimpleNamespace(
        Context=object,
        Event=object,
        Operator=object,
    )
    _module(
        "bpy.props",
        EnumProperty=lambda **_kwargs: None,
        StringProperty=lambda **_kwargs: None,
    )

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

    class GestureMenuRuntime:
        def _draw_menu(self):
            self.draw_order.append('menu')

    class PublicOperator:
        pass

    _module(f"{PACKAGE}.ops.quick_add.draw_gpu", DrawGpu=DrawGpu)
    _module(
        f"{PACKAGE}.gesture.element_preview",
        ElementPreviewAdapter=type("ElementPreviewAdapter", (), {}),
    )
    _module(f"{PACKAGE}.gesture.gesture_draw_gpu", GestureGpuDraw=GestureGpuDraw)
    _module(f"{PACKAGE}.gesture.gesture_handle", GestureHandle=GestureHandle)
    _module(
        f"{PACKAGE}.gesture.gesture_input",
        clear_gesture_item_memos=lambda *_args: None,
        refresh_poll_context_fingerprint=lambda *_args: None,
        refresh_snapshot=lambda *_args: None,
        update_extension_hover=lambda *_args: None,
    )
    _module(f"{PACKAGE}.gesture.menu", GestureMenuRuntime=GestureMenuRuntime)
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
    _module(
        f"{PACKAGE}.utils.input_event",
        POINTER_MOVE_EVENT_TYPES=frozenset({
            "MOUSEMOVE", "INBETWEEN_MOUSEMOVE",
        }),
    )
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

    def test_element_timer_skips_hit_testing_and_redraw_when_unchanged(self):
        redraws = []
        session = types.SimpleNamespace()
        owner = types.SimpleNamespace(
            session=session,
            _refresh_preview_poll_context=lambda *_args, **_kwargs: False,
            tag_redraw=lambda: redraws.append(True),
        )
        event = types.SimpleNamespace(type="TIMER")

        result = preview_module.GesturePreview._modal_element(owner, event)

        self.assertEqual(result, {"PASS_THROUGH"})
        self.assertEqual(redraws, [])
        self.assertFalse(hasattr(session, "event_count"))

    def test_poll_refresh_restores_the_last_pointer_event_for_timer(self):
        pointer_event = types.SimpleNamespace(type="MOUSEMOVE")
        timer_event = types.SimpleNamespace(type="TIMER")
        fingerprint = ("OBJECT", 1)
        session = types.SimpleNamespace(
            event=pointer_event,
            _input_event_serial=3,
            _poll_context_fingerprint=fingerprint,
            _element_status_cache=object(),
        )
        owner = types.SimpleNamespace(session=session)
        original_refresh = preview_module.refresh_poll_context_fingerprint
        try:
            preview_module.refresh_poll_context_fingerprint = (
                lambda current: current._poll_context_fingerprint
            )
            changed = preview_module.GesturePreview._refresh_preview_poll_context(
                owner,
                timer_event,
                restore_event=True,
            )
        finally:
            preview_module.refresh_poll_context_fingerprint = original_refresh

        self.assertFalse(changed)
        self.assertIs(session.event, pointer_event)
        self.assertEqual(session._input_event_serial, 4)

    def test_menu_preview_space_drag_switches_from_centered_to_anchor(self):
        redraws = []
        root = types.SimpleNamespace(rect=(20.0, 30.0, 120.0, 90.0))
        owner = types.SimpleNamespace(
            _menu_centered=True,
            _menu_panels=[root],
            _menu_anchor=(0.0, 0.0),
            _menu_drag_mouse=None,
            _menu_layout_dirty=False,
            _menu_mouse=lambda event: event.point,
            _ensure_layout=lambda **_kwargs: None,
            _tag_menu_redraw=lambda: redraws.append(True),
        )
        press = types.SimpleNamespace(
            type='SPACE', value='PRESS', alt=False, ctrl=False, shift=False,
            point=(40.0, 50.0),
        )
        move = types.SimpleNamespace(
            type='MOUSEMOVE', value='NOTHING', alt=False, ctrl=False, shift=False,
            point=(55.0, 42.0),
        )
        release = types.SimpleNamespace(
            type='SPACE', value='RELEASE', alt=False, ctrl=False, shift=False,
            point=(55.0, 42.0),
        )

        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, press),
            {'RUNNING_MODAL'},
        )
        self.assertFalse(owner._menu_centered)
        self.assertEqual(owner._menu_anchor, (20.0, 90.0))
        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, move),
            {'RUNNING_MODAL'},
        )
        self.assertEqual(owner._menu_anchor, (35.0, 82.0))
        self.assertTrue(owner._menu_layout_dirty)
        self.assertEqual(redraws, [True])
        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, release),
            {'RUNNING_MODAL'},
        )
        self.assertIsNone(owner._menu_drag_mouse)

    def test_menu_preview_can_drag_from_header_with_left_mouse(self):
        redraws = []
        root = types.SimpleNamespace(rect=(10.0, 20.0, 110.0, 80.0))
        owner = types.SimpleNamespace(
            _menu_centered=True,
            _menu_panels=[root],
            _menu_anchor=(0.0, 0.0),
            _menu_drag_mouse=None,
            _menu_drag_button=None,
            _menu_layout_dirty=False,
            _menu_mouse=lambda event: event.point,
            _menu_header_hit=lambda _event: True,
            _ensure_layout=lambda **_kwargs: None,
            _tag_menu_redraw=lambda: redraws.append(True),
        )
        press = types.SimpleNamespace(
            type="LEFTMOUSE", value="PRESS", alt=False, ctrl=False, shift=False,
            point=(30.0, 70.0),
        )
        move = types.SimpleNamespace(
            type="INBETWEEN_MOUSEMOVE", value="NOTHING", alt=False, ctrl=False, shift=False,
            point=(42.0, 75.0),
        )
        release = types.SimpleNamespace(
            type="LEFTMOUSE", value="RELEASE", alt=False, ctrl=False, shift=False,
            point=(42.0, 75.0),
        )

        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, press),
            {"RUNNING_MODAL"},
        )
        self.assertEqual(owner._menu_anchor, (10.0, 80.0))
        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, move),
            {"RUNNING_MODAL"},
        )
        self.assertEqual(owner._menu_anchor, (22.0, 85.0))
        self.assertEqual(redraws, [True])
        self.assertEqual(
            preview_module.GesturePreview._menu_drag_event(owner, release),
            {"RUNNING_MODAL"},
        )
        self.assertIsNone(owner._menu_drag_button)

    def test_menu_preview_routes_events_to_shared_hud_first(self):
        calls = []
        event = types.SimpleNamespace(
            type='LEFTMOUSE', value='PRESS', mouse_x=24, mouse_y=48,
        )
        owner = types.SimpleNamespace(
            event=None,
            _preview_hud_event=lambda current: (
                calls.append(current) or {'RUNNING_MODAL'}
            ),
        )

        result = preview_module.GesturePreview._modal_menu(owner, event)

        self.assertEqual(result, {'RUNNING_MODAL'})
        self.assertIs(owner.event, event)
        self.assertEqual(calls, [event])

    def test_menu_preview_updates_hover_for_inbetween_mousemove(self):
        calls = []
        event = types.SimpleNamespace(
            type='INBETWEEN_MOUSEMOVE',
            value='NOTHING',
        )
        owner = types.SimpleNamespace(
            event=None,
            _menu_closing_at=0.0,
            _preview_hud_event=lambda _event: set(),
            _menu_drag_event=lambda _event: None,
            _update_menu_hover=lambda _event: calls.append('hover') or True,
            _tag_menu_redraw=lambda: calls.append('redraw'),
        )

        result = preview_module.GesturePreview._modal_menu(owner, event)

        self.assertEqual(result, {'PASS_THROUGH'})
        self.assertIs(owner.event, event)
        self.assertEqual(calls, ['hover', 'redraw'])

    def test_menu_preview_draws_menu_then_shared_hud(self):
        draw_order = []
        owner = types.SimpleNamespace(
            _preview_renderer='MENU',
            draw_order=draw_order,
            gpu=types.SimpleNamespace(
                tips=types.SimpleNamespace(
                    __gpu_draw__=lambda: draw_order.append('tips'),
                ),
                gesture_bpu=types.SimpleNamespace(
                    __gpu_draw__=lambda: draw_order.append('selector'),
                ),
            ),
        )
        owner._draw_preview_hud = lambda: (
            preview_module.GesturePreview._draw_preview_hud(owner)
        )

        preview_module.GesturePreview._draw_menu(owner)

        self.assertEqual(draw_order, ['menu', 'tips', 'selector'])


if __name__ == "__main__":
    unittest.main()
