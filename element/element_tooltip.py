"""Runtime operator/property tooltip content and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TooltipDetail:
    label: str
    value: str


@dataclass(frozen=True)
class RuntimeTooltip:
    title: str
    description: str
    details: tuple[TooltipDetail, ...]
    issues: tuple[str, ...]
    color_role: str
    is_error: bool


def _translate(text: str) -> str:
    try:
        from bpy.app.translations import pgettext_iface

        return pgettext_iface(text)
    except (AttributeError, ImportError):
        return text


def _operator_properties(element) -> tuple[dict | None, str]:
    raw = str(getattr(element, "operator_properties", "{}") or "{}").strip()
    try:
        from ..utils.expression import literal_to_dict

        values = literal_to_dict(raw)
    except (ImportError, SyntaxError, TypeError, ValueError):
        return None, raw
    return values, repr(values)


def _operator_python(bl_idname: str, values: dict | None) -> str:
    if not bl_idname:
        return ""
    if values is None:
        return f"bpy.ops.{bl_idname}(...)"
    arguments = ", ".join(
        f"{name}={value!r}" for name, value in values.items()
    )
    return f"bpy.ops.{bl_idname}({arguments})"


def _configured_icons(element) -> tuple[str, ...]:
    names = []
    if getattr(element, "is_property_display", False):
        if (
                getattr(element, "display_property_type", None) == "BOOLEAN"
                and getattr(element, "property_bool_icons_enabled", False)
        ):
            names.extend((
                getattr(element, "property_true_icon", ""),
                getattr(element, "property_false_icon", ""),
            ))
    elif getattr(element, "enabled_icon", False):
        names.append(getattr(element, "icon", ""))
    return tuple(dict.fromkeys(str(name) for name in names if name))


def _icon_diagnostics(element) -> tuple[str, tuple[str, ...]]:
    names = _configured_icons(element)
    if not names:
        return "", ()
    current = ""
    try:
        current = element._gpu_draw_icon_name() or ""
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        pass
    try:
        from ..utils.icons import check_icon

        invalid = tuple(name for name in names if not check_icon(name))
    except (AttributeError, ImportError, ReferenceError, RuntimeError, TypeError):
        invalid = names
    template = _translate("Icon not found: %s")
    return current or names[0], tuple(template % name for name in invalid)


def build_runtime_tooltip(element, *, preview_read_only: bool = False) -> RuntimeTooltip | None:
    """Build translated source metadata plus actionable configuration issues."""
    from .element_status import get_element_status_info, status_info

    info = get_element_status_info(
        element,
        ops=getattr(element, "ops", None),
    )
    is_operator = bool(getattr(element, "is_operator", False))
    is_property = bool(getattr(element, "is_property_display", False))
    issues = []
    if not info.is_valid:
        summary = status_info(info.status).message
        if summary:
            issues.append(summary)
        if info.message and info.message not in issues:
            issues.append(info.message)

    details = []
    if is_operator:
        bl_idname = str(getattr(element, "operator_bl_idname", "") or "")
        values, properties_text = _operator_properties(element)
        details.extend((
            TooltipDetail(
                _translate("Operator ID"),
                bl_idname or _translate("(empty)"),
            ),
            TooltipDetail(_translate("Parameters"), properties_text),
        ))
        context = str(getattr(element, "operator_context", "") or "")
        if context:
            details.append(TooltipDetail(_translate("Context"), context))
        python = _operator_python(bl_idname, values)
        if python:
            details.append(TooltipDetail(_translate("Python"), python))
    elif is_property:
        path = str(getattr(element, "property_context_path", "") or "")
        python = f"bpy.context.{path}" if path else "bpy.context"
        details.extend((
            TooltipDetail(
                _translate("Property Path"),
                path or _translate("(empty)"),
            ),
            TooltipDetail(_translate("Python"), python),
        ))
        try:
            can_reset = bool(
                not preview_read_only
                and element.display_property_is_editable
                and element.display_property_type in {'BOOLEAN', 'INT', 'FLOAT'}
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            can_reset = False
        if can_reset:
            details.append(TooltipDetail(_translate("Reset to Default"), "Backspace"))

    icon, icon_issues = _icon_diagnostics(element)
    if icon:
        details.append(TooltipDetail(_translate("Icon"), icon))
    issues.extend(icon_issues)
    if info.status.is_error and not preview_read_only:
        issues.append(_translate("Click this item to open gesture settings"))

    if not is_operator and not is_property and not issues:
        return None
    title = (
        getattr(element, "source_name_translate", "")
        or getattr(element, "name_translate", "")
        or _translate("Gesture Element")
    )
    return RuntimeTooltip(
        title=str(title),
        description=str(getattr(element, "source_description", "") or ""),
        details=tuple(details),
        issues=tuple(dict.fromkeys(issue for issue in issues if issue)),
        color_role=(
            info.color_role
            if not icon_issues or not info.is_valid
            else "warning"
        ),
        is_error=bool(info.status.is_error),
    )
