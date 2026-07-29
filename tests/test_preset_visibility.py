from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "preset.py"
PACKAGE = "_preset_visibility_test"


class PresetVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = types.ModuleType(PACKAGE)
        root.__path__ = [str(MODULE_PATH.parents[1])]
        utils = types.ModuleType(f"{PACKAGE}.utils")
        utils.__path__ = [str(MODULE_PATH.parent)]
        debug_util = types.ModuleType(f"{PACKAGE}.utils.debug_util")
        debug_util.debug_print = lambda *_args, **_kwargs: None
        cls.public = types.ModuleType(f"{PACKAGE}.utils.public")
        cls.pref = types.ModuleType(f"{PACKAGE}.utils.pref")
        sys.modules.update({
            PACKAGE: root,
            utils.__name__: utils,
            debug_util.__name__: debug_util,
            cls.public.__name__: cls.public,
            cls.pref.__name__: cls.pref,
        })
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.utils.preset",
            MODULE_PATH,
        )
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        for name in tuple(sys.modules):
            if name == PACKAGE or name.startswith(f"{PACKAGE}."):
                sys.modules.pop(name, None)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        for name in (
            "Example Elements and Layout.json",
            "Example Essentials.json",
            "Example Practical Menu.json",
            "Example Property Controls.json",
            "Maya.json",
            "Example Validation States.json",
        ):
            (folder / name).write_text("{}", encoding="utf-8")
        (folder / "ignore.txt").write_text("", encoding="utf-8")
        self.public.PRESET_FOLDER = str(folder)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_uses_independent_example_setting(self):
        debug_property = types.SimpleNamespace(
            debug_mode=True,
            show_example_presets=False,
        )
        self.pref.get_pref = lambda: types.SimpleNamespace(
            debug_property=debug_property,
        )

        self.assertEqual(
            list(self.module.get_preset_gesture_list()),
            ["Maya"],
        )

        debug_property.show_example_presets = True
        self.assertEqual(
            list(self.module.get_preset_gesture_list()),
            [
                "Example Elements and Layout",
                "Example Essentials",
                "Example Practical Menu",
                "Example Property Controls",
                "Example Validation States",
                "Maya",
            ],
        )

    def test_explicit_visibility_override_is_preserved(self):
        self.pref.get_pref = lambda: (_ for _ in ()).throw(AssertionError())
        self.assertEqual(
            list(self.module.get_preset_gesture_list(include_debug_only=False)),
            ["Maya"],
        )
        self.assertEqual(
            list(self.module.get_preset_gesture_list(include_debug_only=True)),
            [
                "Example Elements and Layout",
                "Example Essentials",
                "Example Practical Menu",
                "Example Property Controls",
                "Example Validation States",
                "Maya",
            ],
        )


if __name__ == "__main__":
    unittest.main()
