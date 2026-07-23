"""Run with Blender in background mode to validate real operator RNA."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

from gesture_helper.element.element_status import (  # noqa: E402
    ElementStatus,
    get_element_status,
    get_operator_argument_error,
)


class OperatorElement:
    enabled = True
    is_selected_structure = False
    is_operator = True
    is_property_display = False
    __operator_id_name_is_validity__ = True

    def __init__(self, func, bl_idname, properties):
        self.operator_func = func
        self.operator_bl_idname = bl_idname
        self.operator_properties = repr(properties)

    def check_operator_poll(self):
        return self.operator_func.poll()


def assert_error(properties, expected):
    element = OperatorElement(
        bpy.ops.mesh.primitive_cube_add,
        "mesh.primitive_cube_add",
        properties,
    )
    error = get_operator_argument_error(element)
    assert error is not None and expected in error, (properties, error)


valid = OperatorElement(
    bpy.ops.mesh.primitive_cube_add,
    "mesh.primitive_cube_add",
    {
        "size": 2,
        "enter_editmode": False,
        "align": "WORLD",
        "location": (0.0, 0.0, 0.0),
    },
)
assert get_operator_argument_error(valid) is None
assert_error({"size": "large"}, "expects a number")
assert_error({"size": -1.0}, "outside the allowed range")
assert_error({"enter_editmode": 1}, "expects a boolean")
assert_error({"align": "NOT_AN_ALIGNMENT"}, "unknown enum value")
assert_error({"location": (0.0, 0.0)}, "expects 3 values")
assert_error({"unknown_argument": 1}, "Unknown operator argument")

transform = OperatorElement(
    bpy.ops.transform.translate,
    "transform.translate",
    {
        "value": (0.0, 0.0, 0.0),
        "orient_matrix": (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
    },
)
assert get_operator_argument_error(transform) is None
transform.operator_properties = repr({"orient_matrix": ((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))})
assert "array shape 3 x 3" in get_operator_argument_error(transform)

poll_blocked = OperatorElement(bpy.ops.uv.unwrap, "uv.unwrap", {})
assert get_element_status(poll_blocked) is ElementStatus.POLL_BLOCKED

invalid_before_poll = OperatorElement(
    bpy.ops.uv.unwrap,
    "uv.unwrap",
    {"method": "NOT_A_METHOD"},
)
assert get_element_status(invalid_before_poll) is ElementStatus.INVALID_ARGUMENTS

print(f"ELEMENT_STATUS_SMOKE_OK Blender {bpy.app.version_string}")
