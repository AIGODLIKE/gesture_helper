from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "utils" / "strict_json.py"
SPEC = importlib.util.spec_from_file_location("_gesture_helper_strict_json", MODULE_PATH)
strict_json = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(strict_json)


class StrictJSONTests(unittest.TestCase):
    def test_normal_nested_json_loads(self):
        self.assertEqual(
            strict_json.loads_json_strict('{"outer": {"value": 1}, "items": [2]}'),
            {"outer": {"value": 1}, "items": [2]},
        )
        self.assertEqual(
            strict_json.load_json_strict(StringIO('{"ok": true}')),
            {"ok": True},
        )

    def test_top_level_duplicate_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate.*name"):
            strict_json.loads_json_strict('{"name": 1, "name": 2}')

    def test_nested_duplicate_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate.*shortcut"):
            strict_json.loads_json_strict(
                '{"gesture": {"shortcut": "A", "shortcut": "B"}}'
            )

    def test_runtime_gesture_readers_use_strict_loader(self):
        import_source = (ROOT / "ops" / "export_import.py").read_text(encoding="utf-8")
        persistence_source = (ROOT / "utils" / "gesture_persistence.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("return load_json_strict(file)", import_source)
        self.assertIn("data = load_json_strict(file)", persistence_source)


if __name__ == "__main__":
    unittest.main()
