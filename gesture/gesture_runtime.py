"""Runtime accessors for gesture modal operators (thin session bridge)."""

from __future__ import annotations

import time

import bpy
from mathutils import Vector

from ..utils.public import PublicProperty


class GestureRuntimeMixin(PublicProperty):
    """Bridge ``ops.xxx`` used by element/draw to ``self.session``.

    Do not annotate ``session`` on the class body — Blender 5.x walks operator
    MRO with typing.get_type_hints; an unresolved forward ref breaks RNA
    property registration (e.g. missing ``gesture`` on WM_OT_gesture_operator).
    """

    @property
    def area(self):
        return self.session.area

    @area.setter
    def area(self, value):
        self.session.area = value

    @property
    def screen(self):
        return self.session.screen

    @screen.setter
    def screen(self, value):
        self.session.screen = value

    @property
    def trajectory_tree(self):
        return self.session.trajectory_tree

    @property
    def trajectory_mouse_move(self):
        return self.session.trajectory_mouse_move

    @property
    def trajectory_mouse_move_time(self):
        return self.session.trajectory_mouse_move_time

    @property
    def extension_hover(self):
        return self.session.extension_hover

    @extension_hover.setter
    def extension_hover(self, value):
        self.session.extension_hover = value

    @property
    def event_count(self):
        return self.session.event_count

    @property
    def move_count(self):
        return self.session.move_count

    @property
    def last_mouse_mouse_time(self):
        return self.session.last_mouse_mouse_time

    @last_mouse_mouse_time.setter
    def last_mouse_mouse_time(self, value):
        self.session.last_mouse_mouse_time = value

    @property
    def _gesture_circle_center(self):
        return self.session._gesture_circle_center

    @_gesture_circle_center.setter
    def _gesture_circle_center(self, value):
        self.session._gesture_circle_center = value

    @property
    def __mouse_position__(self) -> Vector:
        return self.session.snapshot.mouse_window

    @property
    def __last_window_position__(self) -> Vector:
        return self.session.trajectory_tree.last_point

    @property
    def __circle_center_window_position__(self) -> Vector:
        center = self.session._gesture_circle_center
        if center is not None:
            return center
        return self.__last_window_position__

    @property
    def __last_region_position__(self) -> Vector | None:
        region = getattr(bpy.context, 'region', None)
        last = self.__last_window_position__
        if region is None or last is None or not self.is_draw_gpu:
            return None
        return Vector((last.x - region.x, last.y - region.y))

    @property
    def __circle_center_region_position__(self) -> Vector | None:
        region = getattr(bpy.context, 'region', None)
        if region is None or not self.is_draw_gpu:
            return None
        center = self.__circle_center_window_position__
        if center is None:
            return None
        return Vector((center.x - region.x, center.y - region.y))

    @property
    def operator_gesture(self):
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None:
            return None
        name = getattr(self, 'gesture', None) or self.session.gesture_name
        return gestures.get(name)

    @property
    def angle(self):
        return self.session.snapshot.angle

    @property
    def angle_unsigned(self) -> float | None:
        return self.session.snapshot.angle_unsigned

    @property
    def direction(self):
        return self.session.snapshot.direction

    @property
    def distance(self) -> float:
        return self.session.snapshot.distance

    @property
    def direction_element(self):
        return self.session.snapshot.direction_element

    @property
    def direction_items(self) -> dict:
        return self.session.snapshot.direction_items

    @property
    def extension_element(self):
        return self.session.snapshot.extension_element

    @property
    def extension_offset_distance(self) -> float:
        return self.session.snapshot.extension_offset_distance

    @property
    def is_draw_gpu(self) -> bool:
        """Live check — do not use snapshot (timer/context can stale it)."""
        if self.session.trajectory_tree.last_point is None:
            return False
        try:
            return bpy.context.screen == self.session.screen
        except (AttributeError, ReferenceError):
            return False

    @property
    def is_window_region_type(self) -> bool:
        region = getattr(bpy.context, 'region', None)
        return region is not None and region.type == 'WINDOW'

    @property
    def find_closest_point(self):
        return self.session.trajectory_tree.find_nearest(self.session.snapshot.mouse_window)

    @property
    def first_mouse_move_time(self) -> float | None:
        move_time = self.session.trajectory_mouse_move_time
        if move_time:
            return move_time[0]
        return None

    @property
    def operator_time(self) -> float | None:
        if move_time := self.first_mouse_move_time:
            return time.time() - move_time
        return None

    @property
    def last_move_mouse_timeout(self) -> bool:
        return (time.time() - self.session.last_mouse_mouse_time) > (
            self.pref.gesture_property.timeout / 1000
        )

    def _tag_redraw_gesture_screen(self):
        from .gesture_input import tag_redraw_gesture_screen
        tag_redraw_gesture_screen(self.session)

    def tag_redraw(self):
        self._tag_redraw_gesture_screen()
