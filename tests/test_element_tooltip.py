from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "element" / "element_tooltip.py"
PACKAGE = "_element_tooltip_test"


def _package(name, path):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


_package(PACKAGE, ROOT)
_package(f"{PACKAGE}.element", ROOT / "element")
_package(f"{PACKAGE}.utils", ROOT / "utils")


class FakeStatus:
    def __init__(self, *, is_error=False):
        self.is_error = is_error


class FakeInfo:
    def __init__(self, *, valid=True, message="", role="valid", is_error=False):
        self.is_valid = valid
        self.message = message
        self.color_role = role
        self.status = FakeStatus(is_error=is_error)


current_info = FakeInfo()
status_module = types.ModuleType(f"{PACKAGE}.element.element_status")
status_module.get_element_status_info = lambda _element, ops=None: current_info
status_module.status_info = lambda _status: types.SimpleNamespace(message="Invalid operator arguments")
sys.modules[status_module.__name__] = status_module

expression = types.ModuleType(f"{PACKAGE}.utils.expression")
expression.literal_to_dict = lambda value: ast.literal_eval(value)
sys.modules[expression.__name__] = expression

icons = types.ModuleType(f"{PACKAGE}.utils.icons")
icons.check_icon = lambda name: name != "MISSING"
sys.modules[icons.__name__] = icons

bpy = types.ModuleType("bpy")
translations = types.ModuleType("bpy.app.translations")
translations.pgettext_iface = lambda text: text
bpy.app = types.SimpleNamespace(translations=translations)
sys.modules["bpy"] = bpy
sys.modules["bpy.app.translations"] = translations

SPEC = importlib.util.spec_from_file_location(
    f"{PACKAGE}.element.element_tooltip",
    MODULE_PATH,
)
tooltip_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tooltip_module
assert SPEC.loader is not None
SPEC.loader.exec_module(tooltip_module)


class FakeOperatorElement:
    is_operator = True
    is_property_display = False
    operator_bl_idname = "mesh.primitive_cube_add"
    operator_properties = "{'size': 2.0, 'enter_editmode': False}"
    operator_context = "INVOKE_DEFAULT"
    source_name_translate = "Add Cube"
    name_translate = "Cube"
    source_description = "Construct a cube mesh"
    enabled_icon = True
    icon = "MISSING"
    ops = None

    def _gpu_draw_icon_name(self):
        return self.icon


class FakePropertyElement:
    is_operator = False
    is_property_display = True
    property_context_path = "scene.render.film_transparent"
    source_name_translate = "Transparent"
    name_translate = "Transparent"
    source_description = "Use transparent film"
    display_property_type = "BOOLEAN"
    property_bool_icons_enabled = False
    ops = None


class ElementTooltipTests(unittest.TestCase):
    def setUp(self):
        global current_info
        current_info = FakeInfo()

    def test_operator_metadata_and_invalid_icon_issue(self):
        tooltip = tooltip_module.build_runtime_tooltip(FakeOperatorElement())
        details = {detail.label: detail.value for detail in tooltip.details}
        self.assertEqual(tooltip.title, "Add Cube")
        self.assertEqual(details["Operator ID"], "mesh.primitive_cube_add")
        self.assertIn("'size': 2.0", details["Parameters"])
        self.assertEqual(details["Context"], "INVOKE_DEFAULT")
        self.assertEqual(
            details["Python"],
            "bpy.ops.mesh.primitive_cube_add(size=2.0, enter_editmode=False)",
        )
        self.assertIn("Icon not found: MISSING", tooltip.issues)
        self.assertEqual(tooltip.color_role, "warning")

    def test_property_path_and_python_expression(self):
        tooltip = tooltip_module.build_runtime_tooltip(FakePropertyElement())
        details = {detail.label: detail.value for detail in tooltip.details}
        self.assertEqual(
            details["Property Path"],
            "scene.render.film_transparent",
        )
        self.assertEqual(
            details["Python"],
            "bpy.context.scene.render.film_transparent",
        )

    def test_status_summary_detail_and_repair_hint(self):
        global current_info
        current_info = FakeInfo(
            valid=False,
            message="'size' expects a number",
            role="error",
            is_error=True,
        )
        tooltip = tooltip_module.build_runtime_tooltip(FakeOperatorElement())
        self.assertIn("Invalid operator arguments", tooltip.issues)
        self.assertIn("'size' expects a number", tooltip.issues)
        self.assertIn("Click this item to open gesture settings", tooltip.issues)
        self.assertTrue(tooltip.is_error)


if __name__ == "__main__":
    unittest.main()
