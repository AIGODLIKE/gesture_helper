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


def iter_element_children(element):
    """Depth-first pre-order over *element*'s subtree (excluding *element*)."""
    yield from iter_elements(element)
