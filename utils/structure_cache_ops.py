"""Structure-cache mutation helpers for PropertyGroups / operators."""

from __future__ import annotations

from .public_cache import PublicCacheFunc
from .cache_state import CacheState


class StructureCacheOps(PublicCacheFunc):
    """structure_changed / cache_clear bound to active gesture when possible."""

    @classmethod
    def mutation_batch(cls):
        """Batch structural cache invalidation until the block exits."""
        return CacheState.batch()

    def _gesture_for_cache(self, gesture=None):
        if gesture is not None:
            return gesture
        try:
            element = self.active_element
            if element is not None:
                return element.parent_gesture
        except AttributeError:
            ...
        try:
            return self.active_gesture
        except AttributeError:
            ...
        return None

    def structure_changed(self, gesture=None):
        """Rebuild structure cache for the active or given gesture."""
        PublicCacheFunc.structure_changed(self._gesture_for_cache(gesture))

    def cache_clear(self, gesture=None):
        """Rebuild structure cache (single gesture when context is available)."""
        self.structure_changed(gesture)
