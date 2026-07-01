"""Deferred and batched cache invalidation."""

from contextlib import contextmanager


class CacheState:
    _batch_depth = 0
    _pending_structure = False
    _pending_derived = False
    _lock_deferred = False
    _full_structure = False
    _dirty_gestures = set()

    @classmethod
    def mark_structure_dirty(cls, gesture=None):
        cls._pending_structure = True
        if gesture is None:
            cls._full_structure = True
            cls._dirty_gestures.clear()
        elif not cls._full_structure:
            cls._dirty_gestures.add(gesture)

    @classmethod
    def mark_derived_dirty(cls):
        if not cls._pending_structure:
            cls._pending_derived = True

    @classmethod
    @contextmanager
    def batch(cls):
        cls._batch_depth += 1
        try:
            yield
        finally:
            cls._batch_depth -= 1
            if cls._batch_depth == 0:
                cls.flush()

    @classmethod
    def request_structure_clear(cls, gesture=None):
        if cls._batch_depth:
            cls.mark_structure_dirty(gesture)
            return False
        from .public_cache import PublicCache
        if not PublicCache.__is_updatable__:
            cls.mark_structure_dirty(gesture)
            cls._lock_deferred = True
            return False
        return True

    @classmethod
    def request_derived_clear(cls):
        if cls._batch_depth:
            cls.mark_derived_dirty()
            return False
        from .public_cache import PublicCache
        if not PublicCache.__is_updatable__:
            cls._pending_derived = True
            cls._lock_deferred = True
            return False
        return True

    @classmethod
    def _reset_structure_state(cls):
        cls._pending_structure = False
        cls._pending_derived = False
        cls._lock_deferred = False
        cls._full_structure = False
        cls._dirty_gestures.clear()

    @classmethod
    def flush(cls):
        from .public_cache import PublicCacheFunc

        if cls._pending_structure:
            if cls._full_structure:
                PublicCacheFunc._cache_clear_impl()
            elif cls._dirty_gestures:
                PublicCacheFunc._structure_changed_impl(*cls._dirty_gestures)
            cls._reset_structure_state()
            return

        if cls._pending_derived:
            cls._pending_derived = False
            cls._lock_deferred = False
            PublicCacheFunc.clear_derived_only()

    @classmethod
    def flush_after_lock(cls):
        if cls._lock_deferred and (cls._pending_structure or cls._pending_derived):
            from .public_cache import PublicCache
            if PublicCache.__is_updatable__:
                cls.flush()
