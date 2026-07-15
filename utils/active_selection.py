"""Active gesture / element / modal-event selection helpers."""

from __future__ import annotations


class ActiveSelection:
    """Resolve the UI-selected gesture tree nodes from the WM store."""

    @property
    def active_gesture(self):
        """Return active gesture from the session WM store."""
        from .gesture_store import get_gesture_store
        try:
            store = get_gesture_store()
            if store is None:
                return None
            index = getattr(store, "index_gesture", None)
            if index is not None:
                return store.gesture[index]
        except IndexError:
            ...

    @property
    def active_element(self):
        """Return active element (cached per gesture, index-synced)."""
        from .selection import resolve_active_element
        return resolve_active_element(self.active_gesture)

    @property
    def active_event(self):
        """Return active modal event on active element."""
        if self.active_element:
            return self.active_element.active_event
        return None
