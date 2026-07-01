"""Element selection helpers (index chain + session cache)."""

from .iteration import iter_elements

_ACTIVE_ATTR = '_gh_active_element'
_SYNC_INDEX = False


def is_syncing_selection_indexes():
    return _SYNC_INDEX


def _set_index_element(collection, index):
    if collection.index_element != index:
        collection.index_element = index


def clear_active_element_cache(gesture):
    """Drop cached active element after structural changes."""
    if gesture is not None:
        setattr(gesture, _ACTIVE_ATTR, None)


def sync_selection_indexes(element):
    """Point index_element on gesture and each ancestor at *element*."""
    global _SYNC_INDEX
    gesture = element.parent_gesture
    if gesture is None:
        return

    _SYNC_INDEX = True
    try:
        root = element.root_parent
        for index, item in enumerate(gesture.element):
            if item == root:
                _set_index_element(gesture, index)
                break

        node = element
        while node.parent_element is not None:
            parent = node.parent_element
            idx = parent.element.values().index(node)
            _set_index_element(parent, idx)
            node = parent
    finally:
        _SYNC_INDEX = False


def _expand_ancestors(element):
    node = element.parent_element
    while node is not None:
        if not node.show_child:
            node.show_child = True
        node = node.parent_element


def resolve_active_element(gesture):
    """Return the selected element for *gesture*, using cache when valid."""
    if gesture is None or not len(gesture.element):
        return None

    cached = getattr(gesture, _ACTIVE_ATTR, None)
    if cached is not None:
        try:
            if cached.radio and cached.parent_gesture == gesture:
                return cached
        except (ReferenceError, AttributeError):
            pass
        clear_active_element_cache(gesture)

    for element in iter_elements(gesture):
        if element.radio:
            setattr(gesture, _ACTIVE_ATTR, element)
            return element
    return None


def apply_radio_selection(element):
    """Select *element* with minimal RNA writes (clear previous + set new)."""
    gesture = element.parent_gesture
    if gesture is None:
        return

    if not element.radio:
        clear_active_element_cache(gesture)
        return

    sync_selection_indexes(element)
    _expand_ancestors(element)

    prev = getattr(gesture, _ACTIVE_ATTR, None)
    cleared = False
    if prev is not None and prev != element:
        try:
            if prev.radio:
                prev['radio'] = False
                cleared = True
        except (ReferenceError, AttributeError):
            prev = None

    if not cleared and prev != element:
        for item in iter_elements(gesture):
            if item.radio and item != element:
                item['radio'] = False

    if not element.radio:
        element['radio'] = True

    setattr(gesture, _ACTIVE_ATTR, element)
