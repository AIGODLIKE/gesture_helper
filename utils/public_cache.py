class PublicCache:
    """
    Gesture
    TODO RENAME

    Element
    TODO MOVE
    """
    # __element_child_cache__ = {}  # 元素子级列表 这个不需要再单独拿出来,直接读取element 就可以拿到

    __element_parent_element_cache__ = {}  # 父级元素
    __element_parent_gesture_cache__ = {}  # 父级手势

    __gesture_element_iteration__ = {}  # 手势子级迭代{gesture:[child_element]}
    __element_child_iteration__ = {}  # 元素子级迭代 {element:[child_element]}
    __is_updatable__ = True

    @staticmethod
    def clear_cache_data():
        cls = PublicCache
        cls.__element_parent_element_cache__.clear()
        cls.__element_parent_gesture_cache__.clear()
        cls.__gesture_element_iteration__.clear()
        cls.__element_child_iteration__.clear()

    @staticmethod
    def init_cache():
        from .public import get_pref
        pref = get_pref()

        cls = PublicCache
        cls.clear_cache_data()

        for gesture in pref.gesture:
            element_iteration = []
            for element in gesture.element:
                element_iteration.extend(cls.from_element_get_data(gesture, element, None, 0))
            cls.__gesture_element_iteration__[gesture] = element_iteration

        print(f'__element_parent_element_cache__\n{cls.__element_parent_element_cache__}\n')
        print(f'__element_parent_gesture_cache__\n{cls.__element_parent_gesture_cache__}\n')
        print(f'__gesture_element_iteration__\n{cls.__gesture_element_iteration__}\n')
        print(f'__element_child_iteration__\n{cls.__element_child_iteration__}\n')
        print(f'__is_updatable__\n{cls.__is_updatable__}\n')

    @staticmethod
    def from_element_get_data(gesture, element, parent_element, level):
        cls = PublicCache
        cls.__element_parent_gesture_cache__[element] = gesture
        cls.__element_parent_element_cache__[element] = parent_element
        element.level = level

        child_iteration = []
        for child in element.element:
            child_iteration.append(child)
            child_iteration.extend(PublicCache.from_element_get_data(gesture, child, element, level + 1))
        cls.__element_child_iteration__[element] = child_iteration
        return child_iteration


class PublicCacheData(PublicCache):
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
        PublicCacheData.init_cache()
        PublicCacheData.gesture_cache_clear()
        PublicCacheData.element_cache_clear()
        PublicCacheData.poll_cache_clear()
        get_pref.cache_clear()
