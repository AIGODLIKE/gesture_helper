from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "session_state.py"
PACKAGE = "_gesture_session_state_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class FakeMenuRuntime:
    force_close_calls = 0

    @classmethod
    def force_close_all(cls):
        cls.force_close_calls += 1


def _load_session_state_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    for package_name, path in (
            ("utils", MODULE_PATH.parent),
            ("gesture", MODULE_PATH.parents[1] / "gesture"),
    ):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = [str(path)]

    _module(
        f"{PACKAGE}.gesture.menu",
        GestureMenuRuntime=FakeMenuRuntime,
    )

    name = f"{PACKAGE}.utils.session_state"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


session_state_module = _load_session_state_module()


class FakePreview:
    def __init__(self):
        self.close_requests = 0
        self.force_cleanup_calls = 0

    def _request_preview_close(self):
        self.close_requests += 1

    def _force_preview_cleanup(self):
        self.force_cleanup_calls += 1


class SessionStatePreviewLifecycleTests(unittest.TestCase):
    def setUp(self):
        state = session_state_module.SessionState
        state.panel_menu_adding = False
        state.gesture_preview_active = False
        state.gesture_preview_scope = ""
        state.gesture_preview_instance = None
        state.gesture_menu_active = False
        state.context_menu_from_button = False
        state.switch_panel_by_space = {}
        state.switch_panel_enum_items = [("VIEW_3D", "3D View", "")]
        FakeMenuRuntime.force_close_calls = 0

    def test_competing_preview_owner_is_rejected(self):
        state = session_state_module.SessionState
        owner = FakePreview()
        competitor = FakePreview()

        self.assertTrue(state.begin_gesture_preview(owner, "GESTURE"))
        self.assertFalse(state.begin_gesture_preview(competitor, "ELEMENT"))

        self.assertIs(state.gesture_preview_instance, owner)
        self.assertEqual(state.gesture_preview_scope, "GESTURE")
        self.assertTrue(state.gesture_preview_active)

    def test_repeated_close_requests_and_end_are_safe(self):
        state = session_state_module.SessionState
        owner = FakePreview()
        self.assertTrue(state.begin_gesture_preview(owner, "ELEMENT"))

        self.assertTrue(state.request_gesture_preview_close())
        self.assertTrue(state.request_gesture_preview_close())
        self.assertEqual(owner.close_requests, 2)
        self.assertIs(state.gesture_preview_instance, owner)

        state.end_gesture_preview(owner)
        state.end_gesture_preview(owner)

        self.assertIsNone(state.gesture_preview_instance)
        self.assertEqual(state.gesture_preview_scope, "")
        self.assertFalse(state.gesture_preview_active)
        self.assertFalse(state.request_gesture_preview_close())

    def test_late_old_owner_cannot_clear_new_owner(self):
        state = session_state_module.SessionState
        old_owner = FakePreview()
        new_owner = FakePreview()

        self.assertTrue(state.begin_gesture_preview(old_owner, "GESTURE"))
        state.end_gesture_preview(old_owner)
        self.assertTrue(state.begin_gesture_preview(new_owner, "ELEMENT"))

        state.end_gesture_preview(old_owner)

        self.assertIs(state.gesture_preview_instance, new_owner)
        self.assertEqual(state.gesture_preview_scope, "ELEMENT")
        self.assertTrue(state.gesture_preview_active)

    def test_clear_forces_preview_cleanup_and_resets_state(self):
        state = session_state_module.SessionState
        owner = FakePreview()
        self.assertTrue(state.begin_gesture_preview(owner, "GESTURE"))
        state.panel_menu_adding = True
        state.gesture_menu_active = True
        state.context_menu_from_button = True
        state.switch_panel_by_space = {"VIEW_3D": "Gesture"}
        state.switch_panel_enum_items = [("IMAGE_EDITOR", "Image Editor", "")]

        state.clear()

        self.assertEqual(owner.force_cleanup_calls, 1)
        self.assertEqual(FakeMenuRuntime.force_close_calls, 1)
        self.assertIsNone(state.gesture_preview_instance)
        self.assertEqual(state.gesture_preview_scope, "")
        self.assertFalse(state.gesture_preview_active)
        self.assertFalse(state.panel_menu_adding)
        self.assertFalse(state.gesture_menu_active)
        self.assertFalse(state.context_menu_from_button)
        self.assertEqual(state.switch_panel_by_space, {})
        self.assertEqual(
            state.switch_panel_enum_items,
            [("VIEW_3D", "3D View", "")],
        )


if __name__ == "__main__":
    unittest.main()
