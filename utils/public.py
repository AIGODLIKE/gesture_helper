from functools import cache
import os
from os.path import dirname, realpath, join, abspath

import bpy
from bpy.props import StringProperty, CollectionProperty
from mathutils import Vector

from .public_cache import PublicCacheFunc, cache_update_lock
from .cache_state import CacheState
from .selection import resolve_active_element

ADDON_FOLDER = dirname(dirname(realpath(__file__)))
PRESET_FOLDER = abspath(join(ADDON_FOLDER, 'src', 'preset'))


def poll_message_active_gesture(cls) -> bool:
    if get_pref().active_gesture is None:
        cls.poll_message_set("No active gesture")
        return False
    return True


def poll_message_active_element(cls) -> bool:
    if get_pref().active_element is None:
        cls.poll_message_set("No active element")
        return False
    return True

TRANSLATE_ID = "gesture"
TRANSLATE_KEY = TRANSLATE_ID + "_keymap"


@cache
def get_pref():
    from .. import __package__ as base_package
    return bpy.context.preferences.addons[base_package].preferences


def tag_redraw():
    """redraw interface"""
    for area in bpy.context.window.screen.areas:
        area.tag_redraw()


def get_debug(key=None) -> bool:
    from .debug_util import get_debug as _get_debug
    return _get_debug(key)


def by_path_set_value(point, data_path: list[str], value) -> None:
    """
    by_path_set_value(bpy, data_path: ['context','scene','render','resolution_x'], 10)

    eq

    bpy.context.scene.render.resolution_x = 10
    """
    if len(data_path) == 0 or point is None:
        print("by_path_set_value set value Error", point, data_path, value)
    elif len(data_path) == 1:
        setattr(point, data_path[0], value)
    else:
        by_path_set_value(getattr(point, data_path[0]), data_path[1:], value)


@cache
def get_gesture_direction_items(iteration):
    direction = {}
    last_selected_structure = None  # Tracks consecutive selection structures
    for item in iteration:
        if item.is_selected_structure:  # Selection structure
            if item.__selected_structure_is_validity__:  # Valid selection structure
                # Poll passed
                poll = (item.is_selected_else or item.poll_bool)
                if poll and (not last_selected_structure or item.is_selected_if):
                    child = get_gesture_direction_items(item.element)
                    direction.update(child)
                    last_selected_structure = item
            continue  # Skip non-structure handling below
        elif item.is_child_gesture or item.is_operator:  # Child gesture or operator
            if item.enabled:
                direction[item.direction] = item
        if item.enabled:  # Reset structure chain when enabled
            last_selected_structure = None
    return direction


@cache
def get_gesture_extension_items(iteration):
    extension = []
    last_selected_structure = None  # Tracks consecutive selection structures
    for item in iteration:
        if item.is_selected_structure:  # Selection structure
            if item.__selected_structure_is_validity__:  # Valid selection structure
                # Poll passed
                poll = (item.is_selected_else or item.poll_bool)
                if poll and (not last_selected_structure or item.is_selected_if):
                    child = get_gesture_extension_items(item.element)
                    extension.extend(child)
                    last_selected_structure = item
            continue  # Skip non-structure handling below
        elif item.is_child_gesture or item.is_operator or item.is_dividing_line:
            # Child gesture, operator, or divider
            if item.enabled:
                extension.append(item)
        if item.enabled:  # Reset structure chain when enabled
            last_selected_structure = None
    return extension


def update_effect(func):
    def w(*args, **kwargs):
        self = args[0]
        name = func.__name__
        before = getattr(self, f'{name}_before', None)
        after = getattr(self, f'{name}_after', None)

        if before:
            before()
        res = func(*args, **kwargs)
        if after:
            after()

        return res

    return w


class PublicProperty(PublicCacheFunc):

    @staticmethod
    def _pref():
        return get_pref()

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

    @property
    def pref(self):
        return self._pref()

    @property
    def draw_property(self):
        return self._pref().draw_property

    @property
    def debug_property(self):
        return self._pref().debug_property

    @property
    def backups_property(self):
        return self._pref().backups_property

    @property
    def other_property(self):
        return self._pref().other_property

    @property
    def gesture_property(self):
        return self._pref().gesture_property

    @property
    def active_gesture(self):
        """Return active gesture."""
        try:
            index = getattr(self.pref, "index_gesture", None)
            if index is not None:
                return self.pref.gesture[index]
        except IndexError:
            ...

    @property
    def active_element(self):
        """Return active element (cached per gesture, index-synced)."""
        return resolve_active_element(self.active_gesture)

    @property
    def active_event(self):
        """Return active modal event on active element."""
        if self.active_element:
            return self.active_element.active_event
        return None

    @classmethod
    def update_state(cls):
        """Sync temporary keymap state for operators."""
        pref = get_pref()
        ag = pref.active_gesture
        ae = pref.active_element
        try:
            if ag:
                ag.__fix_duplicate_name__()
                ag.to_temp_kmi()  # Must run after rename to avoid keymap sync errors
            if ae:
                if ae.element_type == "OPERATOR" and ae.operator_type == "OPERATOR":
                    ae.to_operator_tmp_kmi()
        except Exception as e:
            print('update_state Error', e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    @staticmethod
    def __tn__(text):
        """Translate display name."""
        from ..src.translate import __name_translate__
        return __name_translate__(text)

    @staticmethod
    def __tp__(text):
        """Translate preset name."""
        from ..src.translate import __preset_translate__
        return __preset_translate__(text)

    @property
    def is_debug(self) -> bool:
        return get_debug()

    @property
    def __is_move_element__(self) -> bool:
        """Return whether element move mode is active."""
        return self.__element_move_item__ is not None

    @property
    def __element_move_item__(self) -> "Element":
        """Return element being moved."""
        from ..element.element_cure import ElementCURE
        return ElementCURE.MOVE.move_item

    @property
    def __is_cut_element__(self) -> bool:
        """Return whether element cut mode is active."""
        return self.__element_cut_item__ is not None

    @property
    def __element_cut_item__(self) -> "Element":
        """Return cut element data."""
        from ..element.element_cure import ElementCURE
        return ElementCURE.CUT.__cut_data__

    @staticmethod
    def __get_icon__(key) -> int:
        """Get icon id for key."""
        from .icons import Icons
        return Icons.get(key).icon_id

    @property
    def ___dict_data___(self) -> dict:
        """Return serializable data for this item."""
        from .property import get_property
        return get_property(self)


class PublicOperator(bpy.types.Operator):
    event: 'bpy.types.Event'

    def init_invoke(self, event):
        self.event = event

    def init_modal(self, event):
        self.event = event

    @property
    def is_right_mouse(self):
        return self.event.type == 'RIGHTMOUSE'

    @property
    def is_release(self):
        return self.event.value == 'RELEASE'

    @property
    def is_exit(self):
        return self.is_release or self.is_right_mouse

    @staticmethod
    def tag_redraw():
        tag_redraw()


class PublicUniqueNamePropertyGroup:
    """Unique name property group."""

    names_iteration: list
    __is_check_duplicate_name__ = True

    @staticmethod
    def __generate_new_name__(names, new_name):
        # Ensure unique name; max suffix .999
        if new_name in names:
            base_name = new_name
            count = 1
            while new_name in names:
                new_name = f"{base_name}.{count:03}"
                count += 1
        return new_name

    @property
    def __names__(self):
        return list(map(lambda s: s.name, self.names_iteration))

    @cache_update_lock
    def __fix_duplicate_name__(self):
        names = self.__names__
        if self.__names__.count(self.name) > 1:
            self.name = self.__generate_new_name__(self.__names__, self.name)
        if len(names) != len(set(names)):
            for i in self.names_iteration:
                if self.__names__.count(i.name) > 1:
                    gesture = getattr(i, 'parent_gesture', None)
                    self.structure_changed(gesture)
                    i.name = self.__generate_new_name__(self.__names__, i.name)

    @update_effect
    def rename(self):
        if self.__is_check_duplicate_name__:
            self.__fix_duplicate_name__()
        update_name = getattr(self, "update_name", None)
        if update_name:
            update_name()

    name: StringProperty(
        name='名称',
        description='不允许名称重复,如果名称重复则编号 e.g .001 .002 .999 支持重命名到999',
        update=lambda self, context: self.rename()
    )


class PublicSortAndRemovePropertyGroup:
    index: int
    collection: CollectionProperty

    def _get_index(self):
        return 0

    def _set_index(self, value):
        ...

    index = property(fget=_get_index, fset=_set_index,
                     doc='Set collection index from item index and move items')

    @property
    def is_last(self) -> bool:
        """
        Return whether this item is last in collection (for reordering)
        @rtype: object
        """
        return self == self.collection[-1]

    @property
    def is_first(self) -> bool:
        """
        Return whether this item is first in collection (for reordering)
        @return:
        """
        return self == self.collection[0]

    @update_effect
    def sort(self, is_next):
        col = self.collection
        gl = len(col)
        if is_next:
            if self.is_last:
                col.move(gl - 1, 0)
                self.index = 0
            else:
                col.move(self.index, self.index + 1)
                self.index = self.index + 1
        else:
            if self.is_first:
                col.move(self.index, gl - 1)
                self.index = gl - 1
            else:
                col.move(self.index - 1, self.index)
                self.index = self.index - 1

    @update_effect
    def remove(self):
        self.collection.remove(self.index)


class PublicMouseModal:
    mouse = None

    def start_mouse(self, event):
        self.mouse = Vector((event.mouse_x, event.mouse_y))

    @staticmethod
    def exit():
        bpy.context.area.header_text_set(None)
        bpy.context.window.cursor_set("DEFAULT")

    @staticmethod
    def set_cursor(context, value_mode):
        if cursor := {
            "MOUSE_CHANGES_HORIZONTAL": "MOVE_X",
            "MOUSE_CHANGES_VERTICAL": "MOVE_Y",
            "MOUSE_CHANGES_ARBITRARY": "SCROLL_XY"}.get(value_mode, None):
            context.window.cursor_set(cursor)

    def value_delta(self, event, value_mode):
        input_scale  = 0.01
        if event.shift:
            input_scale = 0.001

        delta = self.get_delta(event, value_mode) * input_scale
        return delta

    def get_delta(self, event, value_mode):
        if value_mode == "MOUSE_CHANGES_HORIZONTAL":
            return event.mouse_x - self.mouse.x
        elif value_mode == "MOUSE_CHANGES_VERTICAL":
            return event.mouse_y - self.mouse.y
        elif value_mode == "MOUSE_CHANGES_ARBITRARY":
            x = event.mouse_x - self.mouse.x
            y = event.mouse_y - self.mouse.y
            if x > y:
                return max(x, y)
            else:
                return min(x, y)
        else:
            raise ValueError("Invalid value mode: %r" % value_mode)
