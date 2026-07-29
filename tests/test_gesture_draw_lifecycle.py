from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "gesture_draw_gpu.py"
PACKAGE = "_gesture_draw_lifecycle_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    gesture_package = _module(f"{PACKAGE}.gesture")
    gesture_package.__path__ = [str(MODULE_PATH.parent)]
    utils_package = _module(f"{PACKAGE}.utils")
    utils_package.__path__ = [str(MODULE_PATH.parents[1] / "utils")]

    fake_bpy = types.ModuleType("bpy")
    fake_bpy.context = types.SimpleNamespace(space_data=None)
    fake_app = types.ModuleType("bpy.app")
    fake_app.__path__ = []
    fake_translations = types.ModuleType("bpy.app.translations")
    fake_translations.pgettext_iface = lambda value: value
    fake_bpy.app = fake_app

    class PublicGpu:
        pass

    stubs = {
        "bpy": fake_bpy,
        "bpy.app": fake_app,
        "bpy.app.translations": fake_translations,
        "gpu": types.ModuleType("gpu"),
        "mathutils": _module("mathutils", Vector=type("Vector", (), {})),
        f"{PACKAGE}.utils.public_gpu": _module(
            f"{PACKAGE}.utils.public_gpu",
            PublicGpu=PublicGpu,
            gpu_draw_begin=lambda: None,
            gpu_draw_end=lambda: None,
        ),
        f"{PACKAGE}.utils.color": _module(
            f"{PACKAGE}.utils.color",
            color_to_srgb=lambda value: value,
        ),
    }
    name = f"{PACKAGE}.gesture.gesture_draw_gpu"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


gesture_draw_gpu = _load_module()
release_calls = []
redraw_calls = []
frozen_selection_calls = []


class _SessionState:
    gesture_preview_active = False
    gesture_preview_scope = ""

_module(
    f"{PACKAGE}.utils.public",
    tag_redraw=lambda: redraw_calls.append("all"),
)
_module(
    f"{PACKAGE}.utils.ui_draw_sync",
    cancel_all=lambda: None,
    tag_gesture_ui_regions=lambda: redraw_calls.append("ui"),
    release_gesture_panel_state=lambda session: release_calls.append(session),
    set_frozen_ui_selection=lambda gesture, element, *, area=None: (
        frozen_selection_calls.append((gesture, element, area)) or (1, 2)
    ),
)
_module(f"{PACKAGE}.utils.session_state", SessionState=_SessionState)


class InvalidatableArea:
    def __init__(self, pointer):
        self.pointer = pointer
        self.invalid = False

    def as_pointer(self):
        if self.invalid:
            raise ReferenceError("Area RNA was removed")
        return self.pointer


class FakeSpaceType:
    @staticmethod
    def draw_handler_add(*_args):
        return object()


class DirectionTipTransitionTests(unittest.TestCase):
    def test_transition_starts_halfway_and_finishes_at_inner_ring(self):
        transition = gesture_draw_gpu._direction_tip_transition

        start = transition(20.0, 20.0, 70.0)
        middle = transition(45.0, 20.0, 70.0)
        end = transition(70.0, 20.0, 70.0)

        self.assertEqual(start, (10.0, 24.0, 0.28, 0.0))
        self.assertAlmostEqual(middle[0], 15.0)
        self.assertAlmostEqual(middle[1], 34.5)
        self.assertAlmostEqual(middle[2], 0.64)
        self.assertAlmostEqual(middle[3], 0.5)
        self.assertEqual(end, (20.0, 45.0, 1.0, 1.0))

    def test_transition_eases_and_clamps_progress(self):
        transition = gesture_draw_gpu._direction_tip_transition

        before = transition(0.0, 20.0, 70.0)
        quarter = transition(32.5, 20.0, 70.0)
        after = transition(100.0, 20.0, 70.0)

        self.assertEqual(before[0], 10.0)
        self.assertAlmostEqual(quarter[3], 0.15625)
        self.assertLess(quarter[0], 12.5)
        self.assertEqual(after, (20.0, 45.0, 1.0, 1.0))


class GestureDrawLifecycleTests(unittest.TestCase):
    def setUp(self):
        cls = gesture_draw_gpu.GestureGpuDraw
        cls.__active_draw_instances__.clear()
        cls.__finishing_draw_instances__.clear()
        cls.__temp_draw_class__.clear()
        cls.__temp_debug_draw_class__.clear()
        gesture_draw_gpu.bpy.context.space_data = types.SimpleNamespace(
            rna_type=FakeSpaceType,
        )
        release_calls.clear()
        redraw_calls.clear()
        frozen_selection_calls.clear()
        _SessionState.gesture_preview_active = False
        _SessionState.gesture_preview_scope = ""

    def test_invalid_area_still_removes_the_registered_instance(self):
        cls = gesture_draw_gpu.GestureGpuDraw
        area = InvalidatableArea(77)
        session = object()
        operator = cls()
        operator.area = area
        operator.session = session
        operator.bl_idname = "wm.gesture_preview"
        operator.pref = types.SimpleNamespace(
            debug_property=types.SimpleNamespace(debug_draw_gpu_mode=False),
        )
        operator._tag_redraw_gesture_screen = lambda: None

        operator.register_draw()
        self.assertIs(cls.__active_draw_instances__[77], operator)
        self.assertEqual(operator._gesture_draw_area_key, 77)

        area.invalid = True
        with patch.object(cls, "_remove_all_draw_handlers") as remove_handlers:
            operator.unregister_draw()

        self.assertEqual(cls.__active_draw_instances__, {})
        self.assertIsNone(operator._gesture_draw_area_key)
        self.assertEqual(release_calls, [session])
        remove_handlers.assert_called_once_with()

    def test_real_gesture_captures_preview_row_before_closing_preview(self):
        cls = gesture_draw_gpu.GestureGpuDraw
        area = InvalidatableArea(88)
        close_trace = []

        class ActivePreview:
            bl_idname = "wm.gesture_preview"

            def __exit_modal__(self):
                close_trace.append("closed")
                _SessionState.gesture_preview_active = False
                _SessionState.gesture_preview_scope = ""

        cls.__active_draw_instances__[88] = ActivePreview()
        _SessionState.gesture_preview_active = True
        _SessionState.gesture_preview_scope = "ELEMENT"

        gesture = object()
        element = types.SimpleNamespace(operator_is_modal=False)
        session = types.SimpleNamespace(area=area)
        operator = cls()
        operator.area = area
        operator.session = session
        operator.bl_idname = "wm.gesture_operator"
        operator.pref = types.SimpleNamespace(
            active_gesture=gesture,
            active_element=element,
            debug_property=types.SimpleNamespace(debug_draw_gpu_mode=False),
        )
        operator._tag_redraw_gesture_screen = lambda: None

        operator.register_draw()

        self.assertEqual(close_trace, ["closed"])
        self.assertFalse(_SessionState.gesture_preview_active)
        self.assertTrue(session._frozen_preview_active)
        self.assertEqual(session._frozen_preview_scope, "ELEMENT")
        self.assertIs(session._frozen_active_gesture, gesture)
        self.assertIs(session._frozen_active_element, element)
        self.assertEqual(frozen_selection_calls, [(gesture, element, area)])
        self.assertIs(cls.__active_draw_instances__[88], operator)


if __name__ == "__main__":
    unittest.main()
