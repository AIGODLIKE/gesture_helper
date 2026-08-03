from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / 'utils' / 'backups.py'
PACKAGE = '_gesture_backup_path_test'


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _BpyUtils:
    def __init__(self):
        self.extension_calls = []
        self.resource_calls = []
        self.extension_result = 'X:/extension-user'
        self.resource_result = 'X:/isolated-datafiles/gesture_helper'
        self.extension_error = None

    def extension_path_user(self, package):
        self.extension_calls.append(package)
        if self.extension_error is not None:
            raise self.extension_error
        return self.extension_result

    def user_resource(self, resource_type, *, path, create):
        self.resource_calls.append((resource_type, path, create))
        return self.resource_result


def _load_backups_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    utils = _module(f'{PACKAGE}.utils')
    utils.__path__ = [str(MODULE_PATH.parent)]
    _module(
        f'{PACKAGE}.utils.strict_json',
        load_json_strict=lambda _handle: {},
        loads_json_strict=lambda _text: {},
    )
    fake_utils = _BpyUtils()
    fake_bpy = types.ModuleType('bpy')
    fake_bpy.utils = fake_utils
    fake_bpy.path = types.SimpleNamespace(abspath=lambda value: value)

    name = f'{PACKAGE}.utils.backups'
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with patch.dict(sys.modules, {'bpy': fake_bpy}):
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return root, module, fake_utils


root_package, backups, bpy_utils = _load_backups_module()


class BackupPathTests(unittest.TestCase):
    def setUp(self):
        bpy_utils.extension_calls.clear()
        bpy_utils.resource_calls.clear()
        bpy_utils.extension_error = None

    def test_legacy_source_does_not_probe_matching_installed_extension(self):
        root_package.__package__ = 'gesture_helper'

        path = backups.get_extension_user_folder(create=False)

        self.assertEqual(path, bpy_utils.resource_result)
        self.assertEqual(bpy_utils.extension_calls, [])
        self.assertEqual(
            bpy_utils.resource_calls,
            [('DATAFILES', 'gesture_helper', False)],
        )

    def test_extension_package_uses_its_extension_user_folder(self):
        root_package.__package__ = 'bl_ext.user_default.gesture_helper'

        path = backups.get_extension_user_folder(create=False)

        self.assertEqual(path, bpy_utils.extension_result)
        self.assertEqual(
            bpy_utils.extension_calls,
            ['bl_ext.user_default.gesture_helper'],
        )
        self.assertEqual(bpy_utils.resource_calls, [])

    def test_extension_path_failure_does_not_fall_back_to_legacy_storage(self):
        root_package.__package__ = 'bl_ext.user_default.gesture_helper'
        bpy_utils.extension_error = RuntimeError('extension path unavailable')

        with self.assertRaisesRegex(RuntimeError, 'extension path unavailable'):
            backups.get_extension_user_folder(create=False)

        self.assertEqual(bpy_utils.resource_calls, [])


if __name__ == '__main__':
    unittest.main()
