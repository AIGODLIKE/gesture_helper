from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "runtime_tooltip.py"
SPEC = importlib.util.spec_from_file_location("_runtime_tooltip_test", MODULE_PATH)
tooltip_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tooltip_module
assert SPEC.loader is not None
SPEC.loader.exec_module(tooltip_module)


class FakeTimers:
    def __init__(self):
        self.registered = []
        self.unregistered = []

    def register(self, callback, *, first_interval):
        self.registered.append((callback, first_interval))

    def unregister(self, callback):
        self.unregistered.append(callback)


class FakeTarget:
    def __init__(self, pointer):
        self.pointer = pointer

    def as_pointer(self):
        return self.pointer


class RuntimeTooltipStateTests(unittest.TestCase):
    def setUp(self):
        self.clock = [10.0]
        self.timers = FakeTimers()
        self.bpy = types.SimpleNamespace(
            app=types.SimpleNamespace(timers=self.timers),
        )

    def test_delay_then_fade_and_redraw(self):
        state = tooltip_module.HoverTooltipState()
        target = FakeTarget(42)
        redraws = []
        with (
            patch.dict(sys.modules, {"bpy": self.bpy}),
            patch.object(
                tooltip_module.time,
                "monotonic",
                side_effect=lambda: self.clock[0],
            ),
        ):
            changed = tooltip_module.sync_hover_tooltip(
                state,
                target,
                delay_ms=100,
                redraw=lambda: redraws.append(self.clock[0]),
            )
            self.assertTrue(changed)
            callback, first_interval = self.timers.registered[-1]
            self.assertAlmostEqual(first_interval, 0.1)
            self.assertEqual(tooltip_module.tooltip_reveal(state, target), 0.0)

            self.clock[0] = 10.1
            self.assertIsNotNone(callback())
            self.assertEqual(redraws, [10.1])
            self.clock[0] = 10.16
            self.assertGreater(tooltip_module.tooltip_reveal(state, target), 0.0)
            self.assertLess(tooltip_module.tooltip_reveal(state, target), 1.0)
            self.clock[0] = 10.23
            self.assertEqual(tooltip_module.tooltip_reveal(state, target), 1.0)
            self.assertIsNone(callback())

    def test_target_change_cancels_old_timer(self):
        state = tooltip_module.HoverTooltipState()
        with (
            patch.dict(sys.modules, {"bpy": self.bpy}),
            patch.object(tooltip_module.time, "monotonic", return_value=2.0),
        ):
            tooltip_module.sync_hover_tooltip(
                state, FakeTarget(1), delay_ms=100, redraw=lambda: None,
            )
            old_timer = state.timer
            tooltip_module.sync_hover_tooltip(
                state, FakeTarget(2), delay_ms=100, redraw=lambda: None,
            )
            self.assertIn(old_timer, self.timers.unregistered)
            tooltip_module.cancel_hover_tooltip(state)
        self.assertIsNone(state.target)
        self.assertIsNone(state.timer)


if __name__ == "__main__":
    unittest.main()
