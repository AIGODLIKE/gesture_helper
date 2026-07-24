from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parent / "blender_live_panel_profile.py"
_load_count = 0


def _context(*, text_editor: bool):
    if text_editor:
        space_data = types.SimpleNamespace(
            type="TEXT_EDITOR",
            text=types.SimpleNamespace(filepath=str(MODULE_PATH)),
        )
    else:
        space_data = types.SimpleNamespace(type="VIEW_3D", text=None)
    return types.SimpleNamespace(space_data=space_data)


def _load_profile_module(*, text_editor: bool, background: bool, environ: dict):
    global _load_count
    _load_count += 1
    name = f"_gesture_live_profile_config_test_{_load_count}"
    fake_bpy = types.ModuleType("bpy")
    fake_bpy.context = _context(text_editor=text_editor)
    fake_bpy.app = types.SimpleNamespace(background=background)

    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with (
        patch.dict(sys.modules, {"bpy": fake_bpy}),
        patch.dict(os.environ, environ, clear=True),
    ):
        assert spec.loader is not None
        spec.loader.exec_module(module)
        remaining_environment = dict(os.environ)
    return module, remaining_environment


class LivePanelProfileConfigurationTests(unittest.TestCase):
    def test_text_editor_run_ignores_all_automation_environment(self):
        module, _remaining = _load_profile_module(
            text_editor=True,
            background=False,
            environ={
                "GH_PROFILE_AUTOMATION": "1",
                "GH_PROFILE_AUTO_QUIT": "1",
                "GH_PROFILE_WARMUP_SECONDS": "0.5",
                "GH_PROFILE_SECONDS": "0.5",
                "GH_PROFILE_REQUIRE_PLAYBACK": "0",
                "GH_PROFILE_REQUIRE_GESTURE_PANEL": "0",
            },
        )

        self.assertFalse(module.AUTOMATION)
        self.assertFalse(module.AUTO_QUIT)
        self.assertEqual(module.WARMUP_SECONDS, 3.0)
        self.assertEqual(module.PROFILE_SECONDS, 10.0)
        self.assertTrue(module.REQUIRE_PLAYBACK)
        self.assertTrue(module.REQUIRE_GESTURE_PANEL)
        self.assertEqual(
            module.CONFIGURATION_SOURCE,
            "interactive_text_editor_fixed",
        )

    def test_auto_quit_alone_does_not_enable_foreground_automation(self):
        module, _remaining = _load_profile_module(
            text_editor=False,
            background=False,
            environ={
                "GH_PROFILE_AUTO_QUIT": "1",
                "GH_PROFILE_WARMUP_SECONDS": "0.5",
                "GH_PROFILE_SECONDS": "0.5",
                "GH_PROFILE_REQUIRE_PLAYBACK": "0",
            },
        )

        self.assertFalse(module.AUTOMATION)
        self.assertFalse(module.AUTO_QUIT)
        self.assertEqual(module.PROFILE_SECONDS, 10.0)
        self.assertTrue(module.REQUIRE_PLAYBACK)
        self.assertTrue(module.REQUIRE_GESTURE_PANEL)

    def test_explicit_automation_uses_overrides_and_consumes_marker(self):
        module, remaining = _load_profile_module(
            text_editor=False,
            background=False,
            environ={
                "GH_PROFILE_AUTOMATION": "1",
                "GH_PROFILE_AUTO_QUIT": "1",
                "GH_PROFILE_WARMUP_SECONDS": "0.25",
                "GH_PROFILE_SECONDS": "0.75",
                "GH_PROFILE_REQUIRE_PLAYBACK": "0",
                "GH_PROFILE_REQUIRE_GESTURE_PANEL": "0",
            },
        )

        self.assertTrue(module.AUTOMATION)
        self.assertTrue(module.AUTO_QUIT)
        self.assertEqual(module.WARMUP_SECONDS, 0.25)
        self.assertEqual(module.PROFILE_SECONDS, 0.75)
        self.assertFalse(module.REQUIRE_PLAYBACK)
        self.assertFalse(module.REQUIRE_GESTURE_PANEL)
        self.assertEqual(module.CONFIGURATION_SOURCE, "explicit_automation")
        self.assertNotIn("GH_PROFILE_AUTOMATION", remaining)

    def test_background_auto_quit_keeps_legacy_smoke_compatible(self):
        module, _remaining = _load_profile_module(
            text_editor=False,
            background=True,
            environ={
                "GH_PROFILE_AUTO_QUIT": "1",
                "GH_PROFILE_WARMUP_SECONDS": "0.25",
                "GH_PROFILE_SECONDS": "0.5",
                "GH_PROFILE_REQUIRE_PLAYBACK": "0",
            },
        )

        self.assertTrue(module.AUTOMATION)
        self.assertTrue(module.AUTO_QUIT)
        self.assertEqual(module.PROFILE_SECONDS, 0.5)
        self.assertFalse(module.REQUIRE_PLAYBACK)
        self.assertEqual(
            module.CONFIGURATION_SOURCE,
            "legacy_background_automation",
        )

    def test_live_status_writes_only_when_state_changes(self):
        module, _remaining = _load_profile_module(
            text_editor=True,
            background=False,
            environ={},
        )
        recorder = object.__new__(module.LivePanelProfile)
        recorder.live_status_state = None
        sidebar = [{"area_pointer": 101, "sidebar_visible": True}]

        with tempfile.TemporaryDirectory() as directory:
            recorder.output_dir = Path(directory)
            recorder._publish_live_status("armed", "First", sidebar)
            status_path = recorder.output_dir / "latest-status.json"
            first_payload = status_path.read_text(encoding="utf-8")

            recorder._publish_live_status("armed", "Ignored", [])
            self.assertEqual(
                status_path.read_text(encoding="utf-8"),
                first_payload,
            )

            recorder._publish_live_status(
                "waiting_for_playback",
                "Start playback",
                sidebar,
            )
            second_payload = status_path.read_text(encoding="utf-8")

        self.assertNotEqual(second_payload, first_payload)
        self.assertIn('"state": "waiting_for_playback"', second_payload)
        self.assertIn('"script_revision": "live-panel-profile-v4"', second_payload)

    def test_frame_summary_reports_forward_skips_and_wraps(self):
        module, _remaining = _load_profile_module(
            text_editor=True,
            background=False,
            environ={},
        )
        recorder = object.__new__(module.LivePanelProfile)
        recorder.scene_at_start = {"frame_start": 1, "frame_end": 10}
        recorder.frame_times = [0.0, 0.1, 0.2, 0.3]
        recorder.frame_values = [9, 10, 2, 4]

        summary = recorder._frame_summary(0.3)

        self.assertEqual(summary["timeline_direction"], "FORWARD")
        self.assertEqual(summary["advanced_frames"], 5)
        self.assertEqual(summary["jump_event_count"], 2)
        self.assertEqual(summary["skipped_frames"], 2)
        self.assertEqual(summary["wrap_count"], 1)
        self.assertAlmostEqual(summary["presented_ratio"], 3 / 5)

    def test_frame_summary_reports_reverse_skips_and_wraps(self):
        module, _remaining = _load_profile_module(
            text_editor=True,
            background=False,
            environ={},
        )
        recorder = object.__new__(module.LivePanelProfile)
        recorder.scene_at_start = {"frame_start": 1, "frame_end": 10}
        recorder.frame_times = [0.0, 0.1, 0.2, 0.3]
        recorder.frame_values = [2, 1, 9, 7]

        summary = recorder._frame_summary(0.3)

        self.assertEqual(summary["timeline_direction"], "REVERSE")
        self.assertEqual(summary["advanced_frames"], 5)
        self.assertEqual(summary["jump_event_count"], 2)
        self.assertEqual(summary["skipped_frames"], 2)
        self.assertEqual(summary["wrap_count"], 1)
        self.assertAlmostEqual(summary["presented_ratio"], 3 / 5)


if __name__ == "__main__":
    unittest.main()
