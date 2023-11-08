class PublicCache:
    """
    Gesture
    TODO RENAME

    Element
    TODO MOVE
    """
    __element_child_cache__ = {}
    __element_parent_element_cache__ = {}
    __element_parent_gesture_cache__ = {}

    __gesture_element_iteration__ = {}


class PublicCacheData:
    @staticmethod
    def gesture_cache_clear():
        print('gesture_cache_clear')
        from .gesture import gesture_relationship
        gesture_relationship.get_element_iteration.cache_clear()
        gesture_relationship.get_gesture_index.cache_clear()

    @staticmethod
    def element_cache_clear():
        print('element_cache_clear')
        from .gesture.element import element_relationship
        element_relationship.get_childes.cache_clear()
        element_relationship.get_parent_gesture.cache_clear()
        element_relationship.get_parent_element.cache_clear()
        element_relationship.get_element_index.cache_clear()

    @staticmethod
    def poll_cache_clear():
        # TODO
        ...

    @staticmethod
    def cache_clear():
        from .public import get_pref
        print('cache_clear')
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        PublicCacheData.poll_cache_clear()
        get_pref.cache_clear()
