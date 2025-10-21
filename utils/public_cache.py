def cache_update_lock(func, cache_clear=False):
    """缓存更新锁"""
    cls = PublicCache

    def wap(*args, **kwargs):
        if cls.__is_updatable__:
            cls.__is_updatable__ = False
            func_return = func(*args, **kwargs)
            cls.__is_updatable__ = True
            if cache_clear:
                PublicCacheFunc.cache_clear()
            return func_return
    return wap


class PublicCache:
    """
    Gesture

    Element
    MOVE
    """

    __element_prev_cache__ = {}  # 上一个element
    __element_child_iteration__ = {}  # 元素子级迭代 {element:[child_element]}
    __element_parent_element_cache__ = {}  # 父级元素
    __element_parent_gesture_cache__ = {}  # 父级手势

    __gesture_element_iteration__ = {}  # 手势子级迭代{gesture:[child_element]}
    __is_updatable__ = True

    @staticmethod
    def cache_clear_data():
        cls = PublicCache
        cls.__element_prev_cache__.clear()
        cls.__element_child_iteration__.clear()
        cls.__element_parent_element_cache__.clear()
        cls.__element_parent_gesture_cache__.clear()

        cls.__gesture_element_iteration__.clear()

    @staticmethod
    def init_cache():
        from .public import get_pref
        pref = get_pref()

        cls = PublicCache
        cls.cache_clear_data()

        def from_collection(g, item):
            element_iteration = []
            prev_element = None
            for element in item.element:
                element_iteration.append(element)
                cls.__element_prev_cache__[element] = prev_element
                prev_element = element

                element_iteration.extend(cls.from_element_get_data(g, element, None, 0))
            return element_iteration

        for gesture in pref.gesture:
            cls.__gesture_element_iteration__[gesture] = from_collection(gesture, gesture)

    @staticmethod
    def from_element_get_data(gesture, element, parent_element, level):
        cls = PublicCache
        cls.__element_parent_gesture_cache__[element] = gesture
        cls.__element_parent_element_cache__[element] = parent_element
        element.level = level

        child_iteration = []

        prev_element = None
        for child in element.element:
            child_iteration.append(child)
            cls.__element_prev_cache__[child] = prev_element
            prev_element = child

            child_iteration.extend(PublicCache.from_element_get_data(gesture, child, element, level + 1))
        cls.__element_child_iteration__[element] = child_iteration

        # modal events parent
        for event in element.modal_events:
            cls.__element_parent_element_cache__[event] = element
        return child_iteration


class PublicCacheFunc(PublicCache):
    @staticmethod
    def gesture_cache_clear():
        from ..gesture import gesture_relationship
        gesture_relationship.get_gesture_index.cache_clear()

    @staticmethod
    def element_cache_clear():
        from ..element import element_relationship
        element_relationship.get_element_index.cache_clear()
        element_relationship.get_available_selected_structure.cache_clear()

    @staticmethod
    def gesture_direction_cache_clear():
        from .public import get_gesture_direction_items
        get_gesture_direction_items.cache_clear()

    @staticmethod
    def gesture_extension_cache_clear():
        from .public import get_gesture_extension_items
        get_gesture_extension_items.cache_clear()

    @staticmethod
    def cache_clear():
        cls = PublicCacheFunc
        if cls.__is_updatable__:
            from .public import get_pref
            get_pref.cache_clear()
            cls.init_cache()
            cls.gesture_cache_clear()
            cls.element_cache_clear()
            cls.gesture_direction_cache_clear()
            cls.gesture_extension_cache_clear()
