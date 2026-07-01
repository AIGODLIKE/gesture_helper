from functools import cache

from bpy.props import BoolProperty, StringProperty

from ..debug import DEBUG_CACHE
from ..utils.iteration import iter_elements
from ..utils.public import PublicSortAndRemovePropertyGroup, get_gesture_direction_items
from ..utils.public_cache import PublicCache, cache_update_lock


@cache
def get_element_index(element) -> int | None:
    try:
        return element.collection.values().index(element)
    except ValueError:
        ...
    return -1


@cache
def get_available_selected_structure(element) -> bool:
    def get_prev(e):
        p = e.prev_element
        if p and not p.enabled:
            return get_prev(p)
        else:
            return p

    prev = get_prev(element)  # Previous item; skip disabled predecessors
    prev_type = getattr(prev, 'selected_type', None)  # Previous item type

    if not element.is_selected_structure:
        # Previous item is not a selection structure
        return False
    elif element.is_selected_if:
        # Previous item is selection structure if
        return element.enabled
    elif element.is_selected_elif or element.is_selected_else:
        if prev_type:
            # Valid if previous is not else and this item is enabled
            return not prev.is_selected_else and prev.__selected_structure_is_validity__ and element.enabled
        else:
            return False
    else:
        Exception('Unexpected selection structure', element)
    return False


class Relationship:
    @property
    def parent(self):
        pe = self.parent_element
        if pe:
            return pe
        else:
            return self.parent_gesture

    @property
    def root_parent(self):
        if self.is_root:
            return self
        else:
            return self.parent_element.root_parent

    @property
    def parent_element(self):
        if self not in PublicCache.__element_parent_element_cache__:
            self.init_cache()
            if DEBUG_CACHE:
                print("parent_element key error", self, self not in PublicCache.__element_parent_element_cache__,
                      PublicCache.__element_parent_element_cache__.get(self))
                print("\tw")
                for k, v in PublicCache.__element_parent_element_cache__.items():
                    print("\t", k, v)
        return PublicCache.__element_parent_element_cache__[self]

    @property
    def parent_gesture(self):
        if self not in PublicCache.__element_parent_gesture_cache__:
            self.init_cache()
            if DEBUG_CACHE:
                print("parent_gesture key error", self, self not in PublicCache.__element_parent_gesture_cache__,
                      PublicCache.__element_parent_gesture_cache__.get(self))
                print("\ts")
                for k, v in PublicCache.__element_parent_gesture_cache__.items():
                    print("\t", k, v)
        return PublicCache.__element_parent_gesture_cache__.get(self)

    @property
    def collection_iteration(self) -> list:
        items = []
        for element in self.parent_gesture.element:
            items.extend(PublicCache.__element_child_iteration__[element])
        return items

    @property
    def collection(self):
        pe = self.parent_element
        if pe:
            return pe.element
        else:
            return self.parent_gesture.element

    @property
    def element_iteration(self):
        """Return all items in the current gesture."""
        return PublicCache.__gesture_element_iteration__[self.parent_gesture]

    @property
    def prev_element(self):
        return PublicCache.__element_prev_cache__[self]

    @property
    def gesture_direction_items(self):
        return get_gesture_direction_items(self.element)

    @property
    def parent_gesture_direction_items(self):
        return self.parent.gesture_direction_items

    @property
    def element_child_iteration(self):
        return PublicCache.__element_child_iteration__[self]


class RadioSelect:
    @staticmethod
    def _live_element_iteration(gesture):
        return list(iter_elements(gesture))

    @cache_update_lock
    def update_radio(self):
        gesture = self.parent_gesture
        if gesture is None:
            self.cache_clear()
            gesture = self.parent_gesture
        if gesture is None:
            return

        try:
            for (index, element) in enumerate(gesture.element):
                if self.root_parent == element:
                    gesture.index_element = index

            if not self.is_root:
                collection = self.collection
                if collection is not None:
                    for index, e in enumerate(collection):
                        if e == self:
                            self.parent.index_element = index
                            break

            for item in self._live_element_iteration(gesture):
                is_select = item == self
                item['radio'] = is_select
                if is_select and self.is_operator:
                    self.to_operator_tmp_kmi()
        except Exception as e:
            self.cache_clear()
            print("update_radio Error", e.args)
            import traceback
            traceback.print_exc()
            traceback.print_stack()

    radio: BoolProperty(name='Radio', update=lambda self, context: self.update_radio())

    @property
    def radio_iteration(self):
        gesture = self.parent_gesture
        if gesture is None:
            return []
        return self._live_element_iteration(gesture)


class ElementRelationship(RadioSelect,
                          PublicSortAndRemovePropertyGroup,
                          Relationship):
    name: StringProperty(name="Name")

    def _get_index(self) -> int:
        return get_element_index(self)

    def _set_index(self, value):
        self.parent.index_element = value

    index = property(
        fget=_get_index,
        fset=_set_index,
        doc='Set collection index from item index and move items')

    @property
    def is_root(self):
        return self in self.parent_gesture.element.values()

    @property
    def names_iteration(self):
        return self.parent_gesture.element_iteration

    @property
    def is_alert(self) -> bool:
        """Return whether warning UI should be shown."""
        if self.is_selected_structure:  # Selection structure
            # Valid selection structure
            if self.enabled:
                return not self.__selected_structure_is_validity__
        elif self.is_operator:
            if self.operator_type == "OPERATOR":
                return not (self.__operator_id_name_is_validity__ and self.__operator_properties_is_validity__)
        return False

    @property
    def __selected_structure_is_validity__(self) -> bool:
        """Return whether this is a valid selection structure."""
        return get_available_selected_structure(self) and self.__poll_bool_is_validity__


    def __init_direction_by_sort__(self):
        """Initialize direction by sort order."""
        ds = list(self.parent_gesture_direction_items.keys())
        for k in range(1, 9):
            s = str(k)
            if s not in ds:
                self.direction = s
                return
