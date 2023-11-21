import traceback


class PublicCache:
    """
    Gesture
    TODO RENAME

    Element
    TODO MOVE
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

        for gesture in pref.gesture:
            element_iteration = []
            prev_element = None
            for element in gesture.element:
                element_iteration.append(element)
                cls.__element_prev_cache__[element] = prev_element
                prev_element = element

                element_iteration.extend(cls.from_element_get_data(gesture, element, None, 0))
            cls.__gesture_element_iteration__[gesture] = element_iteration

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
            cls.__element_prev_cache__[element] = prev_element
            prev_element = child

            child_iteration.extend(PublicCache.from_element_get_data(gesture, child, element, level + 1))
        cls.__element_child_iteration__[element] = child_iteration
        return child_iteration


class PublicCacheFunc(PublicCache):
    @staticmethod
    def gesture_cache_clear():
        from .gesture import gesture_relationship
        gesture_relationship.get_gesture_index.cache_clear()

    @staticmethod
    def element_cache_clear():
        from .gesture.element import element_relationship
        element_relationship.get_element_index.cache_clear()
        element_relationship.get_available_selected_structure.cache_clear()

    @staticmethod
    def poll_cache_clear():
        # TODO
        ...

    @staticmethod
    def cache_clear():
        cls = PublicCacheFunc
        if cls.__is_updatable__:
            caller_name = traceback.extract_stack()[-2][2]
            from .public import get_pref
            print(f'cache_clear 被 {caller_name} 调用')
            cls.init_cache()
            cls.gesture_cache_clear()
            cls.element_cache_clear()
            cls.poll_cache_clear()
            get_pref.cache_clear()
