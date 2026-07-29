"""Coherent GPU overlay themes and interaction-state color helpers.

All values are scene-linear RGBA because Blender ``COLOR`` properties store
scene-linear components.  Renderers remain responsible for their usual GPU or
BLF conversion at the final upload boundary.
"""

from __future__ import annotations

from . import theme_defaults


THEME_PRESET_ITEMS = (
    (
        'BLENDER_DARK',
        'Blender Dark',
        'Neutral dark surfaces with Blender-style blue interaction feedback',
    ),
    (
        'DEEP_GREY',
        'Deep Grey',
        'Blender-inspired deep grey surfaces with a restrained orange accent',
    ),
    (
        'MINIMAL_DARK',
        'Minimal Dark',
        'Minimal deep surfaces with indigo interaction feedback',
    ),
    (
        'BLENDER_LIGHT',
        'Blender Light',
        'Bright Blender-style surfaces with dark text and blue feedback',
    ),
    (
        'MAYA',
        'Maya',
        'Medium neutral surfaces with a cool cyan-blue accent',
    ),
    (
        'CUSTOM',
        'Custom',
        'Keep the individually edited colors below',
    ),
)


THEME_COLOR_FIELDS = (
    'overlay_background_color',
    'overlay_header_color',
    'background_operator_color',
    'background_operator_active_color',
    'background_child_color',
    'background_child_active_color',
    'background_bool_true',
    'background_bool_false',
    'background_int_color',
    'background_int_active_color',
    'background_float_color',
    'background_float_active_color',
    'interaction_hover_color',
    'interaction_pressed_color',
    'text_default_color',
    'text_active_color',
    'text_disabled_color',
    'trajectory_mouse_color',
    'trajectory_gesture_color',
    'dividing_line_color',
    'outline_color',
    'outline_active_color',
    'status_disabled_color',
    'status_warning_color',
    'status_error_color',
)


def _palette(**overrides):
    result = {
        'overlay_background_color': theme_defaults.PANEL_BACKGROUND,
        'overlay_header_color': theme_defaults.HEADER,
        'background_operator_color': theme_defaults.BACKGROUND,
        'background_operator_active_color': theme_defaults.OPERATOR_ACTIVE,
        'background_child_color': theme_defaults.BACKGROUND,
        'background_child_active_color': theme_defaults.CHILD_ACTIVE,
        'background_bool_true': theme_defaults.BOOL_TRUE,
        'background_bool_false': theme_defaults.BOOL_FALSE,
        'background_int_color': theme_defaults.INT,
        'background_int_active_color': theme_defaults.INT_ACTIVE,
        'background_float_color': theme_defaults.FLOAT,
        'background_float_active_color': theme_defaults.FLOAT_ACTIVE,
        'interaction_hover_color': theme_defaults.HOVER,
        'interaction_pressed_color': theme_defaults.PRESSED,
        'text_default_color': theme_defaults.TEXT_DEFAULT,
        'text_active_color': theme_defaults.TEXT_ACTIVE,
        'text_disabled_color': theme_defaults.TEXT_DISABLED,
        'trajectory_mouse_color': theme_defaults.TRAJECTORY_MOUSE,
        'trajectory_gesture_color': theme_defaults.TRAJECTORY_GESTURE,
        'dividing_line_color': theme_defaults.DIVIDING_LINE,
        'outline_color': theme_defaults.OUTLINE,
        'outline_active_color': theme_defaults.OUTLINE_ACTIVE,
        'status_disabled_color': theme_defaults.STATUS_DISABLED,
        'status_warning_color': theme_defaults.STATUS_WARNING,
        'status_error_color': theme_defaults.STATUS_ERROR,
    }
    result.update(overrides)
    if set(result) != set(THEME_COLOR_FIELDS):
        missing = sorted(set(THEME_COLOR_FIELDS) - set(result))
        extra = sorted(set(result) - set(THEME_COLOR_FIELDS))
        raise RuntimeError(f'Invalid theme palette fields: missing={missing}, extra={extra}')
    return result


THEME_PRESETS = {
    'BLENDER_DARK': _palette(),
    'DEEP_GREY': _palette(
        overlay_background_color=(0.026, 0.027, 0.029, 0.985),
        overlay_header_color=(0.080, 0.078, 0.074, 1.0),
        background_operator_color=(0.058, 0.057, 0.055, 0.98),
        background_operator_active_color=(0.42, 0.13, 0.018, 1.0),
        background_child_color=(0.049, 0.048, 0.047, 0.98),
        background_child_active_color=(0.42, 0.13, 0.018, 1.0),
        background_bool_true=(0.42, 0.13, 0.018, 1.0),
        background_bool_false=(0.058, 0.057, 0.055, 0.98),
        background_int_color=(0.058, 0.057, 0.055, 0.98),
        background_int_active_color=(0.32, 0.10, 0.016, 0.94),
        background_float_color=(0.058, 0.057, 0.055, 0.98),
        background_float_active_color=(0.36, 0.12, 0.018, 0.94),
        interaction_hover_color=(0.56, 0.19, 0.025, 1.0),
        interaction_pressed_color=(0.25, 0.070, 0.008, 1.0),
        text_default_color=(0.76, 0.75, 0.72, 1.0),
        text_active_color=(1.0, 0.93, 0.84, 1.0),
        text_disabled_color=(0.40, 0.39, 0.37, 1.0),
        trajectory_mouse_color=(0.52, 0.17, 0.025, 0.72),
        trajectory_gesture_color=(0.72, 0.24, 0.03, 1.0),
        outline_color=(0.19, 0.18, 0.17, 0.94),
        outline_active_color=(0.62, 0.21, 0.026, 0.98),
    ),
    'MINIMAL_DARK': _palette(
        overlay_background_color=(0.010, 0.014, 0.030, 0.985),
        overlay_header_color=(0.027, 0.036, 0.078, 1.0),
        background_operator_color=(0.026, 0.034, 0.068, 0.98),
        background_operator_active_color=(0.090, 0.12, 0.48, 1.0),
        background_child_color=(0.022, 0.029, 0.058, 0.98),
        background_child_active_color=(0.090, 0.12, 0.48, 1.0),
        background_bool_true=(0.090, 0.12, 0.48, 1.0),
        background_bool_false=(0.026, 0.034, 0.068, 0.98),
        background_int_color=(0.026, 0.034, 0.068, 0.98),
        background_int_active_color=(0.065, 0.10, 0.38, 0.94),
        background_float_color=(0.026, 0.034, 0.068, 0.98),
        background_float_active_color=(0.055, 0.15, 0.38, 0.94),
        interaction_hover_color=(0.16, 0.21, 0.72, 1.0),
        interaction_pressed_color=(0.055, 0.070, 0.30, 1.0),
        text_default_color=(0.70, 0.76, 0.90, 1.0),
        text_active_color=(0.94, 0.97, 1.0, 1.0),
        text_disabled_color=(0.34, 0.38, 0.52, 1.0),
        trajectory_mouse_color=(0.14, 0.28, 0.72, 0.72),
        trajectory_gesture_color=(0.20, 0.42, 0.92, 1.0),
        dividing_line_color=(0.090, 0.11, 0.21, 1.0),
        outline_color=(0.075, 0.090, 0.17, 0.94),
        outline_active_color=(0.22, 0.34, 0.86, 0.98),
    ),
    'BLENDER_LIGHT': _palette(
        overlay_background_color=(0.70, 0.72, 0.76, 0.985),
        overlay_header_color=(0.48, 0.51, 0.56, 1.0),
        background_operator_color=(0.58, 0.60, 0.64, 0.98),
        background_operator_active_color=(0.055, 0.25, 0.62, 1.0),
        background_child_color=(0.62, 0.64, 0.68, 0.98),
        background_child_active_color=(0.055, 0.25, 0.62, 1.0),
        background_bool_true=(0.055, 0.25, 0.62, 1.0),
        background_bool_false=(0.58, 0.60, 0.64, 0.98),
        background_int_color=(0.58, 0.60, 0.64, 0.98),
        background_int_active_color=(0.16, 0.38, 0.70, 0.94),
        background_float_color=(0.58, 0.60, 0.64, 0.98),
        background_float_active_color=(0.12, 0.42, 0.66, 0.94),
        interaction_hover_color=(0.12, 0.38, 0.82, 1.0),
        interaction_pressed_color=(0.040, 0.18, 0.50, 1.0),
        text_default_color=(0.025, 0.030, 0.040, 1.0),
        text_active_color=(1.0, 1.0, 1.0, 1.0),
        text_disabled_color=(0.24, 0.26, 0.30, 1.0),
        trajectory_mouse_color=(0.10, 0.32, 0.72, 0.72),
        trajectory_gesture_color=(0.055, 0.25, 0.74, 1.0),
        dividing_line_color=(0.34, 0.36, 0.40, 1.0),
        outline_color=(0.30, 0.32, 0.36, 0.96),
        outline_active_color=(0.055, 0.25, 0.68, 0.98),
        status_disabled_color=(0.38, 0.40, 0.44, 1.0),
    ),
    'MAYA': _palette(
        overlay_background_color=(0.070, 0.076, 0.082, 0.985),
        overlay_header_color=(0.13, 0.14, 0.15, 1.0),
        background_operator_color=(0.105, 0.112, 0.12, 0.98),
        background_operator_active_color=(0.040, 0.30, 0.48, 1.0),
        background_child_color=(0.092, 0.098, 0.105, 0.98),
        background_child_active_color=(0.040, 0.30, 0.48, 1.0),
        background_bool_true=(0.040, 0.30, 0.48, 1.0),
        background_bool_false=(0.105, 0.112, 0.12, 0.98),
        background_int_color=(0.105, 0.112, 0.12, 0.98),
        background_int_active_color=(0.050, 0.24, 0.38, 0.94),
        background_float_color=(0.105, 0.112, 0.12, 0.98),
        background_float_active_color=(0.035, 0.28, 0.40, 0.94),
        interaction_hover_color=(0.055, 0.42, 0.66, 1.0),
        interaction_pressed_color=(0.020, 0.20, 0.34, 1.0),
        text_default_color=(0.72, 0.75, 0.78, 1.0),
        text_active_color=(0.96, 0.99, 1.0, 1.0),
        text_disabled_color=(0.40, 0.43, 0.46, 1.0),
        trajectory_mouse_color=(0.040, 0.36, 0.58, 0.72),
        trajectory_gesture_color=(0.050, 0.52, 0.78, 1.0),
        dividing_line_color=(0.20, 0.21, 0.22, 1.0),
        outline_color=(0.20, 0.21, 0.22, 0.96),
        outline_active_color=(0.060, 0.47, 0.70, 0.98),
    ),
}


def apply_theme_preset(target, identifier: str) -> bool:
    """Assign one complete preset to a DrawProperty-like target."""
    values = THEME_PRESETS.get(str(identifier))
    if values is None:
        return False
    for name in THEME_COLOR_FIELDS:
        setattr(target, name, values[name])
    return True


def blend_color(source, target, amount: float) -> tuple[float, float, float, float]:
    """Blend RGB while preserving the source alpha."""
    source = tuple(float(value) for value in source)
    target = tuple(float(value) for value in target)
    amount = min(1.0, max(0.0, float(amount)))
    alpha = source[3] if len(source) > 3 else 1.0
    return (
        *(source[index] + (target[index] - source[index]) * amount for index in range(3)),
        alpha,
    )


def interaction_color(draw, base, *, hovered=False, pressed=False):
    """Return a consistent normal/hover/pressed surface color."""
    if pressed:
        target = getattr(
            draw,
            'interaction_pressed_color',
            theme_defaults.PRESSED,
        )
        return blend_color(base, target, 0.90)
    if hovered:
        target = getattr(
            draw,
            'interaction_hover_color',
            theme_defaults.HOVER,
        )
        return blend_color(base, target, 0.72)
    return tuple(float(value) for value in base)
