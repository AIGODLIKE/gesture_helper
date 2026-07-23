from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "element" / "element_status.py"
PACKAGE = "_gesture_status_test"


def _install_package(name: str, path: Path) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


_install_package(PACKAGE, MODULE_PATH.parents[1])
_install_package(f"{PACKAGE}.element", MODULE_PATH.parent)
_install_package(f"{PACKAGE}.utils", MODULE_PATH.parents[1] / "utils")

expression = types.ModuleType(f"{PACKAGE}.utils.expression")


def _literal_to_dict(value):
    if isinstance(value, dict):
        return value
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a dictionary")
    return parsed


expression.literal_to_dict = _literal_to_dict
sys.modules[expression.__name__] = expression

gesture_items = types.ModuleType(f"{PACKAGE}.utils.gesture_items")
gesture_items.poll_context_fingerprint = lambda: ()
sys.modules[gesture_items.__name__] = gesture_items

public_cache = types.ModuleType(f"{PACKAGE}.utils.public_cache")
public_cache.PublicCache = type("PublicCache", (), {"__derived_generation__": 0})
sys.modules[public_cache.__name__] = public_cache

SPEC = importlib.util.spec_from_file_location(
    f"{PACKAGE}.element.element_status",
    MODULE_PATH,
)
status_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = status_module
assert SPEC.loader is not None
SPEC.loader.exec_module(status_module)


class FakeProperty:
    def __init__(
            self,
            identifier,
            prop_type,
            *,
            enum_items=(),
            enum_flag=False,
            is_array=False,
            array_length=0,
            array_dimensions=(),
            hard_min=None,
            hard_max=None,
    ):
        self.identifier = identifier
        self.type = prop_type
        self.enum_items = [
            type("EnumItem", (), {"identifier": item})()
            for item in enum_items
        ]
        self.is_enum_flag = enum_flag
        self.is_array = is_array
        self.array_length = array_length
        self.array_dimensions = array_dimensions
        self.hard_min = hard_min
        self.hard_max = hard_max


class FakeOperator:
    def __init__(self, properties):
        self._rna = type("RNA", (), {"properties": properties})()

    def get_rna_type(self):
        return self._rna


class FakeElement:
    enabled = True
    is_selected_structure = False
    is_operator = True
    is_property_display = False
    __operator_id_name_is_validity__ = True
    operator_bl_idname = "test.operator"

    def __init__(self, arguments, properties, *, poll=True):
        self.operator_properties = repr(arguments) if isinstance(arguments, dict) else arguments
        self.operator_func = FakeOperator(properties)
        self._poll = poll

    def check_operator_poll(self):
        return self._poll


class ElementStatusTests(unittest.TestCase):
    def setUp(self):
        self.properties = {
            "enabled": FakeProperty("enabled", "BOOLEAN"),
            "count": FakeProperty("count", "INT", hard_min=1, hard_max=8),
            "factor": FakeProperty("factor", "FLOAT", hard_min=0.0, hard_max=1.0),
            "label": FakeProperty("label", "STRING"),
            "mode": FakeProperty("mode", "ENUM", enum_items=("A", "B")),
            "flags": FakeProperty(
                "flags", "ENUM", enum_items=("X", "Y"), enum_flag=True,
            ),
            "dynamic": FakeProperty("dynamic", "ENUM"),
            "vector": FakeProperty(
                "vector",
                "FLOAT",
                is_array=True,
                array_length=3,
                hard_min=-1.0,
                hard_max=1.0,
            ),
            "matrix": FakeProperty(
                "matrix",
                "FLOAT",
                is_array=True,
                array_length=9,
                array_dimensions=(3, 3, 0),
                hard_min=-1.0,
                hard_max=1.0,
            ),
        }

    def assert_argument_error(self, arguments, text):
        element = FakeElement(arguments, self.properties)
        error = status_module.get_operator_argument_error(element)
        self.assertIsNotNone(error)
        self.assertIn(text, error)

    def test_valid_scalar_enum_flag_dynamic_enum_and_array_values(self):
        element = FakeElement(
            {
                "enabled": True,
                "count": 3,
                "factor": 1,
                "label": "Item",
                "mode": "A",
                "flags": {"X", "Y"},
                "dynamic": "CONTEXT_VALUE",
                "vector": (0, 0.5, 1.0),
                "matrix": (
                    (1.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (0.0, 0.0, 1.0),
                ),
            },
            self.properties,
        )
        self.assertIsNone(status_module.get_operator_argument_error(element))

    def test_unknown_argument_and_malformed_literal(self):
        self.assert_argument_error({"missing": 1}, "Unknown operator argument")
        self.assert_argument_error("not a dictionary", "dictionary")

    def test_scalar_types_are_not_coerced_loosely(self):
        self.assert_argument_error({"enabled": 1}, "expects a boolean")
        self.assert_argument_error({"count": True}, "expects an integer")
        self.assert_argument_error({"factor": False}, "expects a number")
        self.assert_argument_error({"label": 4}, "expects text")

    def test_ranges_and_array_shape_are_checked(self):
        self.assert_argument_error({"count": 9}, "outside the allowed range")
        self.assert_argument_error({"factor": -0.1}, "outside the allowed range")
        self.assert_argument_error({"vector": (0.0, 1.0)}, "expects 3 values")
        self.assert_argument_error({"vector": (0.0, 2.0, 0.0)}, "outside the allowed range")
        self.assert_argument_error(
            {"matrix": ((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))},
            "expects array shape 3 x 3",
        )

    def test_enum_shapes_and_identifiers_are_checked(self):
        self.assert_argument_error({"mode": 1}, "expects an enum identifier")
        self.assert_argument_error({"mode": "C"}, "unknown enum value")
        self.assert_argument_error({"flags": ["X"]}, "expects a set")
        self.assert_argument_error({"flags": {"Z"}}, "unknown enum value")

    def test_invalid_arguments_take_priority_over_poll(self):
        element = FakeElement({"count": "three"}, self.properties, poll=False)
        status = status_module._evaluate_status(element, include_poll=True)
        self.assertIs(status, status_module.ElementStatus.INVALID_ARGUMENTS)
        info = status_module.get_element_status_info(element, include_poll=True)
        self.assertIn("expects an integer", info.message)

    def test_poll_false_has_a_distinct_context_status(self):
        element = FakeElement({}, self.properties, poll=False)
        status = status_module._evaluate_status(element, include_poll=True)
        self.assertIs(status, status_module.ElementStatus.POLL_BLOCKED)
        self.assertEqual(status_module.status_info(status).badge, "CTX")

    def test_invalid_operator_argument_and_poll_badges_are_distinct(self):
        invalid_operator = FakeElement({}, self.properties)
        invalid_operator.operator_func = None
        invalid_operator.__operator_id_name_is_validity__ = False
        invalid_arguments = FakeElement({"count": "three"}, self.properties)
        poll_blocked = FakeElement({}, self.properties, poll=False)

        badges = {
            status_module.get_element_status_info(item).badge
            for item in (invalid_operator, invalid_arguments, poll_blocked)
        }
        self.assertEqual(badges, {"OP", "ARG", "CTX"})


if __name__ == "__main__":
    unittest.main()
