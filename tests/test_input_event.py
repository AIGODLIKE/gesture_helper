from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "input_event.py"
spec = importlib.util.spec_from_file_location("_input_event_test", MODULE_PATH)
input_event = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = input_event
assert spec.loader is not None
spec.loader.exec_module(input_event)


class PointerMoveEventTests(unittest.TestCase):
    def test_normal_and_inbetween_moves_share_one_semantic_set(self):
        self.assertEqual(
            input_event.POINTER_MOVE_EVENT_TYPES,
            {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'},
        )


if __name__ == '__main__':
    unittest.main()
