"""Blender GUI smoke: radial and menu gestures start in Preferences/File Browser areas.

Run WITHOUT --background (area switching crashes headless Blender 5.3):
  blender --factory-startup --python-exit-code 1 --python tests/blender_utility_area_gesture_smoke.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

import bpy

REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert bpy.ops.preferences.addon_enable(module="gesture_helper") == {"FINISHED"}

from gesture_helper.gesture.gesture_draw_gpu import GestureGpuDraw  # noqa: E402
from gesture_helper.gesture.menu import GestureMenuRuntime  # noqa: E402
from gesture_helper.gesture.pass_through.keymap_filter import (  # noqa: E402
    from_region_get_keymaps,
)
from gesture_helper.ops.gesture import GestureOperator  # noqa: E402
from gesture_helper.ops.menu import GestureMenuOperator  # noqa: E402
from gesture_helper.utils.gesture_persistence import (  # noqa: E402
    suppress_gesture_disk_save,
)
from gesture_helper.utils.public import get_pref  # noqa: E402


def make_event(region):
    return SimpleNamespace(
        type="RIGHTMOUSE",
        type_prev="NONE",
        value="PRESS",
        value_prev="NOTHING",
        mouse_x=int(region.x + region.width * 0.5),
        mouse_y=int(region.y + region.height * 0.5),
        mouse_region_x=int(region.width * 0.5),
        mouse_region_y=int(region.height * 0.5),
        mouse_prev_x=int(region.x + region.width * 0.5),
        mouse_prev_y=int(region.y + region.height * 0.5),
        alt=False,
        ctrl=False,
        shift=False,
        oskey=False,
        is_tablet=False,
        pressure=1.0,
    )


# Route a test-only execute through the real invoke callback so the test can
# supply a deterministic RIGHTMOUSE press event.
captured = {}


def _wrap(cls):
    original = cls.invoke

    def execute(self, context):
        captured[cls.__name__] = self
        return original(self, context, make_event(context.region))

    bpy.utils.unregister_class(cls)
    cls.execute = execute
    # No cursor grab: the synthetic event does not come from the window.
    cls.bl_options = set(cls.bl_options) - {"GRAB_CURSOR", "BLOCKING"}
    bpy.utils.register_class(cls)


_wrap(GestureOperator)
_wrap(GestureMenuOperator)

from gesture_helper.utils.gesture_store import get_gestures  # noqa: E402

with suppress_gesture_disk_save():
    gestures = get_gestures()
    gestures.clear()
    radial = gestures.add()
    radial.name = "Utility Radial"
    radial.gesture_type = "RADIAL"
    radial.keymaps = ["Window"]
    element = radial.element.add()
    element.element_type = "OPERATOR"
    element.__init_element__()
    element.name = "Noop"
    element.operator_bl_idname = "wm.redraw_timer"
    menu = gestures.add()
    menu.name = "Utility Menu"
    menu.gesture_type = "MENU"
    menu.keymaps = ["Window"]
    item = menu.element.add()
    item.element_type = "OPERATOR"
    item.__init_element__()
    item.name = "Noop"
    item.operator_bl_idname = "wm.redraw_timer"

CASES = (
    ("PREFERENCES", "SpacePreferences", ["Window"]),
    ("FILE_BROWSER", "SpaceFileBrowser", ["File Browser Main", "File Browser", "Window"]),
)


def check_area(window, area, area_type, space_name, expected_keymaps):
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=window, area=area, region=region):
        assert type(bpy.context.space_data).__name__ == space_name, bpy.context.space_data
        keys = from_region_get_keymaps(bpy.context)
        assert keys == expected_keymaps, (area_type, keys)

        result = bpy.ops.wm.gesture_operator("EXEC_DEFAULT", gesture="Utility Radial")
        assert result == {"RUNNING_MODAL"}, (area_type, "radial", result)
        op = captured.pop("GestureOperator")
        assert GestureGpuDraw.__active_draw_instances__.get(area.as_pointer()) is op
        op.__exit_modal__()
        assert area.as_pointer() not in GestureGpuDraw.__active_draw_instances__

        result = bpy.ops.wm.gesture_menu("EXEC_DEFAULT", gesture="Utility Menu")
        assert result == {"RUNNING_MODAL"}, (area_type, "menu", result)
        menu_op = captured.pop("GestureMenuOperator")
        assert menu_op in GestureMenuRuntime._active_by_area.get(area.as_pointer(), ())
        menu_op._finish_menu(cancelled=True)
        assert not GestureMenuRuntime._active_by_area.get(area.as_pointer())
    print(f"utility area {area_type}: radial + menu OK", flush=True)


state = {"index": 0, "switched": False}


def step():
    try:
        window = bpy.context.window_manager.windows[0]
        area = max(window.screen.areas, key=lambda a: a.width * a.height)
        if state["index"] >= len(CASES):
            area.type = "VIEW_3D"
            bpy.ops.preferences.addon_disable(module="gesture_helper")
            print("UTILITY AREA GESTURE SMOKE OK", flush=True)
            os._exit(0)
        area_type, space_name, expected = CASES[state["index"]]
        if not state["switched"]:
            area.type = area_type
            if area_type == "FILE_BROWSER":
                area.ui_type = "FILES"
            state["switched"] = True
            return 0.5  # let the window manager initialise the new space
        check_area(window, area, area_type, space_name, expected)
        state["index"] += 1
        state["switched"] = False
        return 0.1
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        os._exit(1)


bpy.app.timers.register(step, first_interval=1.0)
