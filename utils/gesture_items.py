"""Gesture direction / extension item walks (poll-aware, not permanently cached).

Selection-structure ``poll_bool`` depends on live Blender context (mode, object,
tool, …). Results must not be frozen with ``functools.cache`` keyed only on the
collection — that made poll look like it stopped working after the first eval.
Per-frame / per-event callers memoize via session keys that include
``poll_context_fingerprint``.
"""

from __future__ import annotations

import bpy


def poll_context_fingerprint() -> tuple:
    """Lightweight fingerprint of context values poll expressions commonly read."""
    context = bpy.context
    obj = getattr(context, 'object', None)
    mode = getattr(context, 'mode', None)
    mesh_select_mode = None
    tool_settings = getattr(context, 'tool_settings', None)
    if tool_settings is not None:
        try:
            mesh_select_mode = tuple(tool_settings.mesh_select_mode)
        except (AttributeError, TypeError):
            mesh_select_mode = None
    try:
        from .expression import get_active_tool_idname
        active_tool = get_active_tool_idname(context)
    except (AttributeError, RuntimeError, TypeError, ImportError):
        active_tool = None
    selected = getattr(context, 'selected_objects', None) or ()
    return (
        mode,
        id(obj) if obj is not None else 0,
        mesh_select_mode,
        active_tool,
        len(selected),
    )


def get_gesture_direction_items(iteration):
    direction = {}
    last_selected_structure = None  # Tracks consecutive selection structures
    for item in iteration:
        if item.is_selected_structure:  # Selection structure
            if item.__selected_structure_is_validity__:  # Valid selection structure
                # Poll passed
                poll = (item.is_selected_else or item.poll_bool)
                if poll and (not last_selected_structure or item.is_selected_if):
                    child = get_gesture_direction_items(item.element)
                    direction.update(child)
                    last_selected_structure = item
            continue  # Skip non-structure handling below
        elif item.is_child_gesture or item.is_operator:  # Child gesture or operator
            if item.enabled:
                direction[item.direction] = item
        if item.enabled:  # Reset structure chain when enabled
            last_selected_structure = None
    return direction


def get_gesture_extension_items(iteration):
    extension = []
    last_selected_structure = None  # Tracks consecutive selection structures
    for item in iteration:
        if item.is_selected_structure:  # Selection structure
            if item.__selected_structure_is_validity__:  # Valid selection structure
                # Poll passed
                poll = (item.is_selected_else or item.poll_bool)
                if poll and (not last_selected_structure or item.is_selected_if):
                    child = get_gesture_extension_items(item.element)
                    extension.extend(child)
                    last_selected_structure = item
            continue  # Skip non-structure handling below
        elif item.is_child_gesture or item.is_operator or item.is_dividing_line:
            # Child gesture, operator, or divider
            if item.enabled:
                extension.append(item)
        if item.enabled:  # Reset structure chain when enabled
            last_selected_structure = None
    return extension
