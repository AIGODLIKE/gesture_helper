from functools import cache

from ..utils.public import (
    get_pref,
    get_gesture_direction_items,
    PublicUniqueNamePropertyGroup,
    PublicSortAndRemovePropertyGroup, )
from ..utils.public_cache import cache_update_lock


@cache
def get_gesture_index(gesture) -> int:
    from ..utils.gesture_store import get_gestures
    gestures = get_gestures()
    if gestures is None:
        return 0
    return gestures.values().index(gesture)


class GestureRelationship(PublicUniqueNamePropertyGroup,
                          PublicSortAndRemovePropertyGroup):

    @property
    def element_iteration(self):
        from ..utils.public_cache import PublicCache
        return PublicCache.__gesture_element_iteration__.get(self, [])

    @property
    def collection_iteration(self) -> list:
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        return gestures.values() if gestures is not None else []

    @property
    def names_iteration(self):
        return self.collection_iteration

    def _get_index_(self) -> int:
        return get_gesture_index(self)

    def _set_index_(self, value: int) -> None:
        from ..utils.gesture_store import get_gesture_store
        store = get_gesture_store()
        if store is not None:
            store.index_gesture = value

    index = property(fget=_get_index_, fset=_set_index_, doc='Set collection index from item index and move items')

    @property
    def collection(self):
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None:
            raise RuntimeError("Gesture store unavailable")
        return gestures

    @property
    def is_enable(self) -> bool:
        """
        @rtype: bool
        """
        return get_pref().enabled and self.enabled

    @property
    def gesture_direction_items(self):
        return get_gesture_direction_items(self.element)

    def remove_before(self):
        # Release this gesture's cached RNA proxies while they are still
        # valid; Blender may reuse the collection pointer identities right
        # after remove(), and stale keys would then resolve to dead items.
        from ..utils.public_cache import PublicCacheFunc
        from .gesture_keymap import drop_gesture_temp_state
        PublicCacheFunc.prepare_gesture_removal(self)
        drop_gesture_temp_state(self)
        if self.is_last and self.index != 0:  # Deleted item was last
            self.index = self.index - 1  # Decrement index to keep a selection

    @cache_update_lock
    def rename_before(self):
        from .gesture_keymap import drop_gesture_temp_state
        drop_gesture_temp_state(self)
        self.to_temp_kmi()
