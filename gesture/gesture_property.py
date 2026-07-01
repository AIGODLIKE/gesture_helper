import math
import time

import bpy
from bpy.props import IntProperty, BoolProperty
from mathutils import Vector

from ..utils.public import PublicProperty
from ..utils.public_cache import cache_update_lock


class GestureProperty(PublicProperty):
    timer = None

    @cache_update_lock
    def copy(self) -> None:
        """Copy this gesture."""
        from ..utils.property import get_property, __set_prop__
        copy_data = get_property(self)
        __set_prop__(self.pref, 'gesture', {'0': copy_data})

    def update_index(self, _) -> None:
        """Update element index selection."""
        from ..utils.selection import is_syncing_selection_indexes

        if is_syncing_selection_indexes():
            return
        try:
            el = self.element.values()[self.index_element]
            if el and not el.radio:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='索引', update=update_index, options={"HIDDEN"})

    enabled: BoolProperty(
        default=True,
        update=lambda self, context: self.key_update(),
        options={"HIDDEN"}
    )

    @property
    def is_active(self) -> bool:
        """Return whether this gesture is active."""
        return self.pref.active_gesture == self

    @property
    def __mouse_position__(self) -> Vector:
        """mouse position"""
        return Vector((self.event.mouse_x, self.event.mouse_y))

    @property
    def __last_window_position__(self) -> Vector:
        """Last mouse window position."""
        return self.trajectory_tree.last_point

    @property
    def __last_region_position__(self) -> Vector:
        """Last mouse region position."""
        region = bpy.context.region
        if self.is_draw_gpu:
            x, y = self.__last_window_position__
            return Vector(((x - region.x), (y - region.y)))
        return False

    @property
    def operator_gesture(self) -> 'GestureProperty | None':
        """
        Gesture currently executing in the operator
        :return:
        """
        return self.pref.gesture.get(self.gesture)

    @property
    def angle(self) -> float:  # Angle in degrees
        """Current gesture angle."""
        if self.is_draw_gpu:
            vector = self.__last_window_position__ - self.__mouse_position__
            if vector == Vector((0, 0)):
                return False  # not move mouse
            angle = (180 * vector.angle_signed(Vector((-1, 0)), Vector((0, 0)))) / math.pi
            return angle
        return False

    @property
    def angle_unsigned(self) -> float | None:
        """Current gesture angle (unsigned)."""
        angle = self.angle
        if angle is not None:
            aa = abs(angle)
            if aa == angle:
                return angle
            else:
                return 360 + angle
        return None

    def _direction_items_context_id(self):
        """Identity of the gesture tree level used for direction slot lookup."""
        tree = self.trajectory_tree
        last_element = tree.last_element if len(tree) else None
        if last_element is not None:
            return id(last_element)
        og = self.operator_gesture
        return id(og) if og is not None else None

    def _raw_direction_items_dict(self):
        """Direction slot map without memo (safe during cache key / extension checks)."""
        tree = self.trajectory_tree
        last_element = tree.last_element if len(tree) else None
        og = self.operator_gesture
        if last_element:
            return last_element.gesture_direction_items
        if og:
            return og.gesture_direction_items
        return {}

    @property
    def direction(self) -> int:
        """Current gesture direction (1-9)."""
        angle = self.angle_unsigned
        if angle is bool:
            return False
        if angle > 337.5:
            return 1
        d = int((angle + 22.5) // 45 + 1)
        if self.is_have_extension_item and self.is_beyond_extension_offset_distance:
            # Adjust direction when mouse is in extension zone
            if d in (6, 8):
                bottom = self._raw_direction_items_dict().get("9", None)
                if bottom and bottom.mouse_is_in_extension_vertical_area or len(self.extension_hover) > 1:
                    return 7
        return d

    @property
    def distance(self) -> float:
        """Current gesture drag distance."""
        if self.is_draw_gpu:
            return (self.__last_window_position__ - self.__mouse_position__).magnitude
        return 0

    @property
    def direction_element(self) -> 'GestureElement':
        """Element on the current direction."""
        return self.direction_items.get(str(self.direction), None)

    @property
    def direction_items(self) -> dict[str, 'GestureElement']:
        """Direction elements (9 slots); later duplicates win."""
        if not self.is_draw_gpu:
            return self._raw_direction_items_dict()

        from ..utils.public_cache import PublicCache
        key = (
            self._direction_items_context_id(),
            PublicCache.__derived_generation__,
        )
        memo = getattr(self, '_direction_items_memo', None)
        if memo is not None and memo[0] == key:
            return memo[1]

        items = self._raw_direction_items_dict()
        self._direction_items_memo = (key, items)
        return items

    @property
    def extension_element(self):
        items = self.direction_items
        if "9" in items:
            return items["9"]
        return None

    @property
    def extension_offset_distance(self) -> float:
        """Extension item offset distance."""
        if self.extension_element:
            offset_position = getattr(self.extension_element, "extension_offset_start_position", None)
            if offset_position:
                return (self.__last_region_position__ - offset_position).magnitude
        return 0

    @property
    def is_beyond_extension_offset_distance(self) -> bool:
        """Return whether gesture exceeds extension offset."""
        return self.distance > self.extension_offset_distance

    @property
    def is_draw_gpu(self) -> bool:
        """Return whether GPU drawing is active (screen + trajectory point)."""
        context_screen = self.screen
        screen_ok = bpy.context.screen == context_screen
        is_ok = self.trajectory_tree.last_point is not None
        return is_ok and screen_ok

    @property
    def is_window_region_type(self) -> bool:
        """Return whether region type is WINDOW."""
        return bpy.context.region.type == 'WINDOW'

    @property
    def is_beyond_threshold(self) -> bool:
        """Return whether distance exceeds threshold."""
        scale = bpy.context.preferences.view.ui_scale
        return self.distance > (self.gesture_property.threshold * scale)

    @property
    def is_beyond_threshold_confirm(self) -> bool:
        """Return whether distance exceeds confirm threshold."""
        scale = bpy.context.preferences.view.ui_scale
        gesture_property = self.gesture_property
        return self.distance > ((gesture_property.threshold_confirm + gesture_property.threshold) * scale)

    @property
    def is_access_child_gesture(self) -> bool:
        """Return whether child gesture can be entered."""
        element = self.direction_element
        return self.is_beyond_threshold_confirm and element and element.is_child_gesture

    @property
    def operator_time(self) -> float | None:
        """Elapsed time since first mouse move."""
        if move_time := self.first_mouse_move_time:
            return time.time() - move_time
        return None

    @property
    def is_draw_gesture(self) -> bool:
        """Return whether gesture trail should be drawn."""
        if self.draw_trajectory_mouse_move:
            return True
        is_timeout = self.last_move_mouse_timeout
        if is_timeout:
            # Timed out
            self.draw_trajectory_mouse_move = True
        return is_timeout

    @property
    def find_closest_point(self) -> [Vector, int, float]:
        """
        Find nearest trajectory point
        https://docs.blender.org/api/master/mathutils.kdtree.html#mathutils.kdtree.KDTree.find
        :return: (Vector, index, distance)
        """
        tree = self.trajectory_tree.kd_tree
        tree.balance()
        return tree.find((*self.__mouse_position__, 0))

    @property
    def first_mouse_move_time(self) -> float | None:
        """
        Time of first mouse move
        :return:
        """
        move_time = self.trajectory_mouse_move_time
        if len(move_time):
            return move_time[-1]
        return None

    @property
    def last_move_mouse_timeout(self) -> bool:  # Last mouse move timed out
        return (time.time() - self.last_mouse_mouse_time) > (self.pref.gesture_property.timeout / 1000)
