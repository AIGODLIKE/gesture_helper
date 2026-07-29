from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "gesture_executor.py"
PACKAGE = "_gesture_executor_status_test"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


package = _module(PACKAGE)
package.__path__ = [str(MODULE_PATH.parents[1])]
gesture_package = _module(f"{PACKAGE}.gesture")
gesture_package.__path__ = [str(MODULE_PATH.parent)]
old_bpy_modules = {
    name: sys.modules.get(name)
    for name in ("bpy", "bpy.app", "bpy.app.translations")
}
bpy = _module("bpy", ops=types.SimpleNamespace())
bpy.__path__ = []
bpy_app = _module("bpy.app")
bpy_app.__path__ = []
translations = _module(
    "bpy.app.translations",
    pgettext=lambda text: text,
)
bpy.app = bpy_app
bpy_app.translations = translations
_module(
    f"{PACKAGE}.gesture.gesture_session",
    GestureSession=object,
    UiHandoff=types.SimpleNamespace(DEFERRED=object()),
)

spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.gesture.gesture_executor",
    MODULE_PATH,
)
executor_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = executor_module
assert spec.loader is not None
spec.loader.exec_module(executor_module)
for module_name, old_module in old_bpy_modules.items():
    if old_module is None:
        sys.modules.pop(module_name, None)
    else:
        sys.modules[module_name] = old_module


class GestureExecutorStatusTests(unittest.TestCase):
    def _run_immediate(self, status):
        element = types.SimpleNamespace(
            is_operator=True,
            is_property_display=False,
            is_layout_container=False,
        )
        session = types.SimpleNamespace(
            snapshot=types.SimpleNamespace(
                direction_element=element,
                threshold_zone=types.SimpleNamespace(is_confirm=True),
            ),
            phase=types.SimpleNamespace(shows_radial_ui=True),
        )
        ops = types.SimpleNamespace(
            gesture_property=types.SimpleNamespace(immediate_implementation=True),
        )
        valid = object()
        status_module = _module(
            f"{PACKAGE}.element.element_status",
            ElementStatus=types.SimpleNamespace(VALID=valid),
            get_element_status=lambda _element, ops=None: status,
        )
        element_package = _module(f"{PACKAGE}.element")
        element_package.__path__ = []
        executor = executor_module.GestureExecutor()
        with patch.dict(sys.modules, {
            element_package.__name__: element_package,
            status_module.__name__: status_module,
        }), patch.object(executor, "try_running_operator", return_value=True) as run:
            result = executor.try_immediate_implementation(session, ops)
        return result, run, valid

    def test_invalid_item_does_not_immediately_exit(self):
        invalid = object()
        result, run, _valid = self._run_immediate(invalid)
        self.assertFalse(result)
        run.assert_not_called()

    def test_valid_item_keeps_immediate_execution(self):
        # Build the status module inline so the returned object is exactly VALID.
        element = types.SimpleNamespace(
            is_operator=True,
            is_property_display=False,
            is_layout_container=False,
        )
        session = types.SimpleNamespace(
            snapshot=types.SimpleNamespace(
                direction_element=element,
                threshold_zone=types.SimpleNamespace(is_confirm=True),
            ),
            phase=types.SimpleNamespace(shows_radial_ui=True),
        )
        ops = types.SimpleNamespace(
            gesture_property=types.SimpleNamespace(immediate_implementation=True),
        )
        valid = object()
        status_module = _module(
            f"{PACKAGE}.element.element_status",
            ElementStatus=types.SimpleNamespace(VALID=valid),
            get_element_status=lambda _element, ops=None: valid,
        )
        element_package = _module(f"{PACKAGE}.element")
        element_package.__path__ = []
        executor = executor_module.GestureExecutor()
        with patch.dict(sys.modules, {
            element_package.__name__: element_package,
            status_module.__name__: status_module,
        }), patch.object(executor, "try_running_operator", return_value=True) as run:
            result = executor.try_immediate_implementation(session, ops)

        self.assertTrue(result)
        run.assert_called_once_with(session, ops)

    def test_layout_validates_the_main_leaf_before_immediate_execution(self):
        main = object()
        layout = types.SimpleNamespace(
            is_operator=False,
            is_property_display=False,
            is_layout_container=True,
            main_element=main,
        )
        session = types.SimpleNamespace(
            snapshot=types.SimpleNamespace(
                direction_element=layout,
                threshold_zone=types.SimpleNamespace(is_confirm=True),
            ),
            phase=types.SimpleNamespace(shows_radial_ui=True),
        )
        ops = types.SimpleNamespace(
            gesture_property=types.SimpleNamespace(immediate_implementation=True),
        )
        valid = object()
        checked = []
        status_module = _module(
            f"{PACKAGE}.element.element_status",
            ElementStatus=types.SimpleNamespace(VALID=valid),
            get_element_status=lambda element, ops=None: checked.append(element),
        )
        element_package = _module(f"{PACKAGE}.element")
        element_package.__path__ = []
        executor = executor_module.GestureExecutor()
        with patch.dict(sys.modules, {
            element_package.__name__: element_package,
            status_module.__name__: status_module,
        }), patch.object(executor, "try_running_operator") as run:
            result = executor.try_immediate_implementation(session, ops)

        self.assertFalse(result)
        self.assertEqual(checked, [main])
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
