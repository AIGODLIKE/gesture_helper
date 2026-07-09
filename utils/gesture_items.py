"""Cached gesture direction / extension item walks."""

from functools import cache


@cache
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


@cache
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
