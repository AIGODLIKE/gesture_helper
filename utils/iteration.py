"""Live element-tree iteration (single source of truth for tree walks)."""

from collections import deque


def iter_elements(root, *, include_root=False):
    """Depth-first pre-order over element collections under *root*.

    *root* is a gesture or element PropertyGroup with an ``element`` collection.
    Yields wrappers taken directly from the live RNA collections, so every
    yielded element is attached by construction.
    """
    if include_root:
        yield root
    stack = deque(root.element)
    while stack:
        element = stack.popleft()
        yield element
        children = element.element
        if len(children):
            stack.extendleft(reversed(children))


def find_owning_gesture(item):
    """Return the gesture PropertyGroup that owns *item*."""
    from .gesture_store import get_gestures

    gestures = get_gestures()
    if gestures is None:
        return None
    for gesture in gestures:
        if item == gesture:
            return gesture
        for element in iter_elements(gesture):
            if element == item:
                return gesture
            for event in element.modal_events:
                if event == item:
                    return gesture
    return None
