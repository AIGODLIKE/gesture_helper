"""Registered Blender smoke test for simultaneous persistent-menu runtimes."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))


assert bpy.ops.preferences.addon_enable(module="gesture_helper") == {"FINISHED"}

from gesture_helper.gesture.menu import GestureMenuRuntime  # noqa: E402
from gesture_helper.ops.menu import GestureMenuOperator  # noqa: E402


window = bpy.context.window
area = next(candidate for candidate in window.screen.areas if candidate.type == "VIEW_3D")
region = next(candidate for candidate in area.regions if candidate.type == "WINDOW")
override = {"window": window, "area": area, "region": region}
window_key = window.as_pointer()
area_key = area.as_pointer()
draw_order = []


class GestureRef:
    def __init__(self, name, pointer):
        self.name = name
        self._pointer = pointer

    def as_pointer(self):
        return self._pointer


def make_runtime(name, rect, gesture):
    runtime = GestureMenuRuntime()
    runtime._menu_area = area
    runtime._menu_gesture_ref = gesture
    runtime._menu_close_requested = False
    runtime._menu_last_draw_error = ""
    runtime._menu_tooltip_state = None
    runtime._draw_menu = lambda: draw_order.append(name)
    runtime._ensure_layout = lambda: None
    runtime._menu_contains = lambda point: (
        rect[0] <= point[0] <= rect[2]
        and rect[1] <= point[1] <= rect[3]
    )
    return runtime


first_gesture = GestureRef("First Gesture", 101)
second_gesture = GestureRef("Second Gesture", 102)
first = make_runtime("first", (10.0, 10.0, 110.0, 110.0), first_gesture)
second = make_runtime("second", (50.0, 50.0, 150.0, 150.0), second_gesture)

try:
    assert not GestureMenuRuntime._active_by_window
    assert not GestureMenuRuntime._active_by_area
    assert not GestureMenuRuntime._draw_handles

    with bpy.context.temp_override(**override):
        assert first._register_menu_runtime(bpy.context)
        assert second._register_menu_runtime(bpy.context)
        assert GestureMenuRuntime._active_by_window[window_key] == (first, second)
        assert GestureMenuRuntime._active_by_area[area_key] == (first, second)
        assert len(GestureMenuRuntime._draw_handles) == 1
        assert not first._menu_close_requested
        assert not second._menu_close_requested
        assert not first._menu_is_topmost()
        assert second._menu_is_topmost()
        assert first._menu_is_obscured_at((75.0, 75.0))
        assert not first._menu_is_obscured_at((25.0, 25.0))

        GestureMenuRuntime._draw_callback()
        assert draw_order == ["first", "second"], draw_order
        assert GestureMenuRuntime._menu_context_instance() is second

        duplicate = make_runtime(
            "duplicate",
            (80.0, 80.0, 180.0, 180.0),
            first_gesture,
        )
        assert duplicate._registered_menu_for_gesture(first_gesture) is first
        first._menu_close_requested = True
        first._menu_closing_at = 10.0
        assert GestureMenuOperator._activate_existing_menu(
            duplicate,
            first_gesture,
        )
        assert GestureMenuRuntime._active_by_window[window_key] == (second, first)
        assert GestureMenuRuntime._active_by_area[area_key] == (second, first)
        assert not first._menu_close_requested
        assert first._menu_closing_at == 0.0

        draw_order.clear()
        GestureMenuRuntime._draw_callback()
        assert draw_order == ["second", "first"], draw_order
        assert "duplicate" not in draw_order
        assert GestureMenuRuntime._menu_context_instance() is first

        first._unregister_menu_runtime()
        assert GestureMenuRuntime._active_by_window[window_key] == (second,)
        assert GestureMenuRuntime._active_by_area[area_key] == (second,)
        assert GestureMenuRuntime._draw_handles

        draw_order.clear()
        GestureMenuRuntime._draw_callback()
        assert draw_order == ["second"], draw_order

        second._unregister_menu_runtime()
        assert not GestureMenuRuntime._active_by_window
        assert not GestureMenuRuntime._active_by_area
        assert not GestureMenuRuntime._draw_handles
finally:
    GestureMenuRuntime.force_close_all()
    bpy.ops.preferences.addon_disable(module="gesture_helper")


print(f"BLENDER_MULTI_MENU_SMOKE_OK {bpy.app.version_string}")
