"""Shared element validity states for Blender UI and GPU overlays."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math

from ..utils.expression import literal_to_dict
from ..utils.gesture_items import poll_context_fingerprint
from ..utils.public_cache import PublicCache


class ElementStatus(str, Enum):
    VALID = "VALID"
    DISABLED = "DISABLED"
    POLL_BLOCKED = "POLL_BLOCKED"
    INVALID_OPERATOR = "INVALID_OPERATOR"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    INVALID_PROPERTY = "INVALID_PROPERTY"
    READ_ONLY_PROPERTY = "READ_ONLY_PROPERTY"
    INVALID_STRUCTURE = "INVALID_STRUCTURE"

    @property
    def is_error(self) -> bool:
        return self in {
            ElementStatus.INVALID_OPERATOR,
            ElementStatus.INVALID_ARGUMENTS,
            ElementStatus.INVALID_PROPERTY,
            ElementStatus.INVALID_STRUCTURE,
        }

    @property
    def is_warning(self) -> bool:
        return self in {
            ElementStatus.POLL_BLOCKED,
            ElementStatus.READ_ONLY_PROPERTY,
        }


@dataclass(frozen=True)
class ElementStatusInfo:
    status: ElementStatus
    badge: str
    message: str
    color_role: str

    @property
    def is_valid(self) -> bool:
        return self.status is ElementStatus.VALID


_STATUS_INFO = {
    ElementStatus.VALID: ElementStatusInfo(
        ElementStatus.VALID, "", "", "valid",
    ),
    ElementStatus.DISABLED: ElementStatusInfo(
        ElementStatus.DISABLED, "OFF", "Element disabled", "disabled",
    ),
    ElementStatus.POLL_BLOCKED: ElementStatusInfo(
        ElementStatus.POLL_BLOCKED, "CTX", "Unavailable in this context", "warning",
    ),
    ElementStatus.INVALID_OPERATOR: ElementStatusInfo(
        ElementStatus.INVALID_OPERATOR, "OP", "Operator not found", "error",
    ),
    ElementStatus.INVALID_ARGUMENTS: ElementStatusInfo(
        ElementStatus.INVALID_ARGUMENTS, "ARG", "Invalid operator arguments", "error",
    ),
    ElementStatus.INVALID_PROPERTY: ElementStatusInfo(
        ElementStatus.INVALID_PROPERTY, "PATH", "Property path not found", "error",
    ),
    ElementStatus.READ_ONLY_PROPERTY: ElementStatusInfo(
        ElementStatus.READ_ONLY_PROPERTY, "LOCK", "Property is read-only", "warning",
    ),
    ElementStatus.INVALID_STRUCTURE: ElementStatusInfo(
        ElementStatus.INVALID_STRUCTURE, "IF", "Invalid condition structure", "error",
    ),
}


def status_info(status: ElementStatus) -> ElementStatusInfo:
    return _STATUS_INFO[status]


def _value_type_name(value) -> str:
    return type(value).__name__


def _number_in_range(prop, value) -> bool:
    if isinstance(value, float) and not math.isfinite(value):
        return False
    minimum = getattr(prop, "hard_min", None)
    maximum = getattr(prop, "hard_max", None)
    if minimum is not None and value < minimum:
        return False
    return maximum is None or value <= maximum


def _scalar_argument_error(prop, value) -> str | None:
    prop_type = prop.type
    name = prop.identifier
    if prop_type == "BOOLEAN":
        if type(value) is not bool:
            return f"'{name}' expects a boolean, got {_value_type_name(value)}"
    elif prop_type == "INT":
        if type(value) is not int:
            return f"'{name}' expects an integer, got {_value_type_name(value)}"
        if not _number_in_range(prop, value):
            return f"'{name}' is outside the allowed range"
    elif prop_type == "FLOAT":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"'{name}' expects a number, got {_value_type_name(value)}"
        if not _number_in_range(prop, value):
            return f"'{name}' is outside the allowed range"
    elif prop_type == "STRING":
        if not isinstance(value, str):
            return f"'{name}' expects text, got {_value_type_name(value)}"
        length_max = getattr(prop, "length_max", 0)
        if length_max and len(value) > length_max:
            return f"'{name}' exceeds the maximum text length"
    elif prop_type == "POINTER":
        if value is not None and not hasattr(value, "bl_rna"):
            return f"'{name}' expects Blender data, got {_value_type_name(value)}"
    elif prop_type == "COLLECTION":
        if not isinstance(value, (list, tuple)):
            return f"'{name}' expects a collection, got {_value_type_name(value)}"
    return None


def _array_argument_error(prop, value) -> str | None:
    name = prop.identifier
    dimensions = tuple(
        dimension
        for dimension in getattr(prop, "array_dimensions", ())
        if dimension
    )
    if not dimensions:
        array_length = getattr(prop, "array_length", 0)
        dimensions = (array_length,) if array_length else ()

    def validate_dimension(sequence, depth):
        if not isinstance(sequence, (list, tuple)):
            return f"'{name}' expects an array"
        if dimensions and len(sequence) != dimensions[depth]:
            if len(dimensions) == 1:
                return f"'{name}' expects {dimensions[0]} values, got {len(sequence)}"
            shape = " x ".join(str(item) for item in dimensions)
            return f"'{name}' expects array shape {shape}"
        if depth + 1 < len(dimensions):
            for item in sequence:
                error = validate_dimension(item, depth + 1)
                if error is not None:
                    return error
            return None
        for item in sequence:
            error = _scalar_argument_error(prop, item)
            if error is not None:
                return error
        return None

    return validate_dimension(value, 0)


def get_operator_argument_error(element) -> str | None:
    """Return a static RNA argument error without invoking the operator.

    Empty enum item lists are treated as dynamic enums and only type-checked.
    Blender resolves those identifiers using the real execution context.
    """
    try:
        values = literal_to_dict(element.operator_properties)
    except (SyntaxError, TypeError, ValueError):
        return "Operator arguments must be a dictionary of literal values"

    func = element.operator_func
    if func is None:
        return "Operator not found"
    try:
        properties = func.get_rna_type().properties
        for name, value in values.items():
            prop = properties.get(name)
            if prop is None or name == "rna_type":
                return f"Unknown operator argument: '{name}'"
            if getattr(prop, "is_readonly", False):
                return f"Operator argument is read-only: '{name}'"
            if prop.type == "ENUM":
                identifiers = {item.identifier for item in prop.enum_items}
                if getattr(prop, "is_enum_flag", False):
                    if not isinstance(value, (set, frozenset)):
                        return f"'{name}' expects a set of enum identifiers"
                    if any(not isinstance(item, str) for item in value):
                        return f"'{name}' expects a set of enum identifiers"
                    unknown = set(value) - identifiers if identifiers else set()
                    if unknown:
                        return f"'{name}' has unknown enum value: {next(iter(unknown))}"
                elif not isinstance(value, str):
                    return f"'{name}' expects an enum identifier"
                elif identifiers and value not in identifiers:
                    return f"'{name}' has unknown enum value: {value}"
                continue

            if getattr(prop, "is_array", False):
                error = _array_argument_error(prop, value)
                if error is not None:
                    return error
                continue

            error = _scalar_argument_error(prop, value)
            if error is not None:
                return error
    except (
            AttributeError,
            KeyError,
            OverflowError,
            ReferenceError,
            RuntimeError,
            TypeError,
            ValueError,
    ):
        return "Unable to inspect operator arguments"
    return None


def _operator_arguments_are_valid(element) -> bool:
    return get_operator_argument_error(element) is None


def _evaluate_status(element, *, include_poll: bool) -> ElementStatus:
    if not getattr(element, "enabled", True):
        return ElementStatus.DISABLED

    if getattr(element, "is_selected_structure", False):
        from .element_relationship import get_available_selected_structure

        if not get_available_selected_structure(element):
            return ElementStatus.INVALID_STRUCTURE
        if not element.__poll_bool_is_validity__:
            return ElementStatus.INVALID_STRUCTURE
        return ElementStatus.VALID

    if getattr(element, "is_operator", False):
        if not element.__operator_id_name_is_validity__:
            return ElementStatus.INVALID_OPERATOR
        if not _operator_arguments_are_valid(element):
            return ElementStatus.INVALID_ARGUMENTS
        if include_poll:
            try:
                if not element.check_operator_poll():
                    return ElementStatus.POLL_BLOCKED
            except (AttributeError, KeyError, ReferenceError, RuntimeError, TypeError):
                return ElementStatus.POLL_BLOCKED
        return ElementStatus.VALID

    if getattr(element, "is_property_display", False):
        if not element.__property_path_is_validity__:
            return ElementStatus.INVALID_PROPERTY
        if not element.display_property_is_editable:
            return ElementStatus.READ_ONLY_PROPERTY

    return ElementStatus.VALID


def get_element_status(element, *, ops=None, include_poll: bool = True) -> ElementStatus:
    """Return a status cached once per modal event and context fingerprint."""
    if ops is None:
        ops = getattr(element, "ops", None)
    session = getattr(ops, "session", None)
    if session is None:
        return _evaluate_status(element, include_poll=include_poll)

    event_key = (
        PublicCache.__derived_generation__,
        getattr(session, "event_count", 0),
    )
    context_packed = getattr(session, "_element_status_context", None)
    if include_poll and (context_packed is None or context_packed[0] != event_key):
        context_packed = (event_key, poll_context_fingerprint())
        session._element_status_context = context_packed
    context_key = context_packed[1] if include_poll else None
    key = (*event_key, context_key)
    packed = getattr(session, "_element_status_cache", None)
    if packed is None or packed[0] != key:
        values = {}
        session._element_status_cache = (key, values)
    else:
        values = packed[1]

    cache_key = (element, include_poll)
    result = values.get(cache_key)
    if result is None:
        result = _evaluate_status(element, include_poll=include_poll)
        values[cache_key] = result
    return result


def get_element_status_info(element, *, ops=None, include_poll: bool = True) -> ElementStatusInfo:
    info = status_info(get_element_status(element, ops=ops, include_poll=include_poll))
    if info.status is ElementStatus.INVALID_ARGUMENTS:
        message = get_operator_argument_error(element)
        if message:
            return replace(info, message=message)
    if info.status is ElementStatus.INVALID_OPERATOR:
        bl_idname = getattr(element, "operator_bl_idname", "")
        if bl_idname:
            return replace(info, message=f"Operator not found: {bl_idname}")
    if info.status is ElementStatus.INVALID_PROPERTY:
        data_path = getattr(element, "property_data_path", "")
        if data_path:
            return replace(info, message=f"Property path not found: {data_path}")
    return info
