"""Live element-tree iteration (single source of truth for tree walks)."""


def iter_elements(root, *, include_root=False):
    """Depth-first pre-order over element collections under *root*.

    *root* is a gesture or element PropertyGroup with an ``element`` collection.
    """
    if include_root:
        yield root
    stack = list(root.element)
    while stack:
        element = stack.pop(0)
        yield element
        if len(element.element):
            stack[0:0] = list(element.element)


def find_owning_gesture(item):
    """Return the gesture PropertyGroup that owns *item*."""
    from .public import get_pref

    for gesture in get_pref().gesture:
        if item == gesture:
            return gesture
        for element in iter_elements(gesture):
            if element == item:
                return gesture
            for event in element.modal_events:
                if event == item:
                    return gesture
    return None
