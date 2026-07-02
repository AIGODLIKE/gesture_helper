"""Element selection helpers (index chain + session cache)."""

from contextlib import contextmanager

from .iteration import iter_elements
from .public_cache import PublicCache, PublicCacheFunc

_ACTIVE_ATTR = '_gh_active_element'
_SYNC_INDEX = False


@contextmanager
def suppress_radio_updates():
    """Batch RNA writes without re-entrant radio update callbacks."""
    prev = PublicCache._suppress_radio_update
    PublicCache._suppress_radio_update = True
    try:
        yield
    finally:
        PublicCache._suppress_radio_update = prev


def _element_is_live(element) -> bool:
    """Return whether *element* is still attached to its collection."""
    try:
        collection = element.collection
        if collection is None:
            return False
        return element in collection.values()
    except (ReferenceError, AttributeError, TypeError):
        return False


def clear_all_active_element_caches(pref=None):
    """Drop cached active-element pointers on every gesture."""
    if pref is None:
        from .public import get_pref
        pref = get_pref()
    gestures = getattr(pref, 'gesture', None)
    if gestures is None:
        return
    for gesture in gestures:
        clear_active_element_cache(gesture)


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


def strip_radio_from_copy_data(data):
    """Remove radio flags from exported element data (and nested children)."""
    if not isinstance(data, dict):
        return data
    data.pop('radio', None)
    children = data.get('element')
    if isinstance(children, dict):
        for child in children.values():
            strip_radio_from_copy_data(child)
    return data


def enforce_single_selection(element):
    """Select only *element*, clearing all other radios without re-entrant updates."""
    if element is None or not _element_is_live(element):
        return

    gesture = element.parent_gesture
    if gesture is None:
        PublicCacheFunc.ensure_item_structure(element)
        gesture = element.parent_gesture
    if gesture is None:
        return

    with suppress_radio_updates():
        for item in iter_elements(gesture):
            if item == element or not _element_is_live(item):
                continue
            if item.radio:
                item['radio'] = False
        if not element.radio:
            element['radio'] = True
        sync_selection_indexes(element)
        _expand_ancestors(element)
        setattr(gesture, _ACTIVE_ATTR, element)


def select_element(element):
    """Make *element* the sole selected item in its gesture."""
    enforce_single_selection(element)


def apply_radio_selection(element):
    """Select *element* with minimal RNA writes (clear previous + set new)."""
    if not _element_is_live(element):
        return

    gesture = element.parent_gesture
    if gesture is None:
        return

    if not element.radio:
        clear_active_element_cache(gesture)
        return

    enforce_single_selection(element)
