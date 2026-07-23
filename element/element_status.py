"""Shared element validity states for Blender UI and GPU overlays."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


def _operator_arguments_are_valid(element) -> bool:
    """Check literal shape and RNA names without invoking the operator."""
    try:
        values = literal_to_dict(element.operator_properties)
    except (SyntaxError, TypeError, ValueError):
        return False

    func = element.operator_func
    if func is None:
        return False
    try:
        properties = func.get_rna_type().properties
        for name, value in values.items():
            prop = properties.get(name)
            if prop is None or name == "rna_type":
                return False
            if prop.type == "ENUM":
                identifiers = {item.identifier for item in prop.enum_items}
                if getattr(prop, "is_enum_flag", False):
                    if not isinstance(value, (set, frozenset)) or not set(value) <= identifiers:
                        return False
                elif not isinstance(value, str) or value not in identifiers:
                    return False
    except (AttributeError, KeyError, ReferenceError, RuntimeError, TypeError):
        return False
    return True


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
    return status_info(get_element_status(element, ops=ops, include_poll=include_poll))
