"""Element selection helpers (index chain + session cache)."""

from contextlib import contextmanager

from .iteration import iter_elements
from .public_cache import PublicCache, PublicCacheFunc

_ACTIVE_ATTR = '_gh_active_element'
_SYNC_INDEX = False
_NO_ACTIVE_ELEMENT = object()
_CACHE_MISS = object()
_ACTIVE_ELEMENT_CACHE: dict[int, object] = {}


def _rna_identity(value) -> int:
    if value is None:
        return 0
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


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
    _ACTIVE_ELEMENT_CACHE.clear()
    from .gesture_store import get_gestures
    gestures = get_gestures()
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
        _ACTIVE_ELEMENT_CACHE.pop(_rna_identity(gesture), None)
        # Remove the legacy proxy-local entry when reloading over an older
        # build. New lookups use the stable module cache above.
        try:
            setattr(gesture, _ACTIVE_ATTR, None)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            ...


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

    gesture_key = _rna_identity(gesture)
    cached = _ACTIVE_ELEMENT_CACHE.get(gesture_key, _CACHE_MISS)
    if cached is _NO_ACTIVE_ELEMENT:
        return None
    if cached is not _CACHE_MISS:
        try:
            if (
                    cached.radio
                    and _rna_identity(cached.parent_gesture) == gesture_key
            ):
                return cached
        except (ReferenceError, AttributeError):
            pass
        clear_active_element_cache(gesture)

    for element in iter_elements(gesture):
        if element.radio:
            _ACTIVE_ELEMENT_CACHE[gesture_key] = element
            return element
    _ACTIVE_ELEMENT_CACHE[gesture_key] = _NO_ACTIVE_ELEMENT
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
        _ACTIVE_ELEMENT_CACHE[_rna_identity(gesture)] = element


def select_element(element):
    """Make *element* the sole selected item in its gesture."""
    enforce_single_selection(element)


def focus_element_settings(element) -> bool:
    """Select an element and its gesture in the existing editor state."""
    if element is None or not _element_is_live(element):
        return False
    gesture = element.parent_gesture
    if gesture is None:
        return False

    from .gesture_store import get_gesture_store
    store = get_gesture_store()
    if store is None:
        return False
    try:
        gesture_index = store.gesture.values().index(gesture)
    except (AttributeError, ReferenceError, ValueError):
        return False

    if store.index_gesture != gesture_index:
        store.index_gesture = gesture_index
    select_element(element)
    try:
        from .public import get_pref
        get_pref().show_page = 'GESTURE'
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        pass
    return True


def reveal_element_settings(element) -> bool:
    """Focus an element, then open the add-on's existing preferences editor."""
    if not focus_element_settings(element):
        return False
    try:
        import bpy
        result = bpy.ops.wm.gesture_show_preferences('EXEC_DEFAULT')
    except (AttributeError, RuntimeError, TypeError):
        return False
    return 'FINISHED' in result


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
