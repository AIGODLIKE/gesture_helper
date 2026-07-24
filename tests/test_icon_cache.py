from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "utils" / "icons.py"
MODULE_NAME = "gesture_helper_icon_cache_test.utils.icons"


def _load_icons_module():
    package = types.ModuleType("gesture_helper_icon_cache_test")
    package.__path__ = []
    utils_package = types.ModuleType("gesture_helper_icon_cache_test.utils")
    utils_package.__path__ = []

    bpy = types.ModuleType("bpy")
    bpy.__path__ = []
    bpy_utils = types.ModuleType("bpy.utils")
    bpy_utils.__path__ = []
    previews = types.ModuleType("bpy.utils.previews")
    bpy_utils.previews = previews
    bpy.utils = bpy_utils

    replacements = {
        package.__name__: package,
        utils_package.__name__: utils_package,
        "bpy": bpy,
        "bpy.utils": bpy_utils,
        "bpy.utils.previews": previews,
    }
    previous = {name: sys.modules.get(name) for name in replacements}
    sys.modules.update(replacements)
    try:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        for name, old_module in previous.items():
            if old_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_module
    return module


icons_module = _load_icons_module()


class _Preview:
    icon_size = (16, 16)
    icon_pixels = (1,)
    icon_pixels_float = ()


class _PreviewCollection:
    def __init__(self, preview):
        self.preview = preview
        self.lookups = 0

    def __getitem__(self, _key):
        self.lookups += 1
        return self.preview


class IconCacheTests(unittest.TestCase):
    def setUp(self):
        icons_module._loaded_previews.clear()

    def test_loaded_preview_skips_repeated_disk_and_pixel_validation(self):
        preview = _Preview()
        collection = _PreviewCollection(preview)
        icons_module.icons = collection
        icons_module.icons_path_map = {"direction": "direction.png"}

        with (
                patch.object(icons_module.os.path, "isfile", return_value=True) as isfile,
                patch.object(
                    icons_module,
                    "_preview_is_empty",
                    wraps=icons_module._preview_is_empty,
                ) as is_empty,
        ):
            first = icons_module.ensure_preview_loaded("Direction")
            second = icons_module.ensure_preview_loaded("Direction.png")

        self.assertIs(first, preview)
        self.assertIs(second, preview)
        self.assertEqual(collection.lookups, 1)
        self.assertEqual(isfile.call_count, 1)
        self.assertEqual(is_empty.call_count, 1)


if __name__ == "__main__":
    unittest.main()
