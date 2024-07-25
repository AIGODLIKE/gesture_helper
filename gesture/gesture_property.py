import math
import time

import bpy
from bpy.props import IntProperty, BoolProperty
from mathutils import Vector

from ..utils.public import PublicProperty
from ..utils.public_cache import cache_update_lock


class GestureProperty(PublicProperty):

    @cache_update_lock
    def copy(self):
        from ..utils import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self)
        PropertySetUtils.set_prop(self.pref, 'gesture', {'0': copy_data})

    def update_index(self, _):
        try:
            el = self.element.values()[self.index_element]
            if el:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='索引', update=update_index)

    enabled: BoolProperty(
        default=True,
        name='启用此手势',
        description="""启用禁用此手势,主要是keymap的更新""",
        update=lambda self, context: self.key_update()
    )

    @property
    def is_active(self):
        return self.pref.active_gesture == self

    @property
    def event_window_position(self):
        return Vector((self.event.mouse_x, self.event.mouse_y))

    @property
    def event_region_position(self):
        region = bpy.context.region
        return Vector((self.event.mouse_x - region.x, self.event.mouse_y - region.y))

    @property
    def last_window_position(self):
        return self.trajectory_tree.last_point

    @property
    def last_region_position(self):
        region = bpy.context.region
        if self.is_draw_gpu:
            x, y = self.last_window_position
            return Vector(((x - region.x), (y - region.y)))
        return False

    @property
    def operator_gesture(self):  # 当前操作符执行的手势
        return self.pref.gesture.get(self.gesture)

    @property
    def angle(self) -> float:  # 角度
        if self.is_draw_gpu:
            vector = self.last_window_position - self.event_window_position
            if vector == Vector((0, 0)):
                return False  # not move mouse
            angle = (180 * vector.angle_signed(Vector((-1, 0)), Vector((0, 0)))) / math.pi
            return angle
        return False

    @property
    def angle_unsigned(self):
        angle = self.angle
        if angle is not None:
            aa = abs(angle)
            if aa == angle:
                return angle
            else:
                return 360 + angle

    @property
    def direction(self) -> int:  # 方向
        angle = self.angle_unsigned
        if angle is bool:
            return False
        if angle > 337.5:
            return 1
        return int((angle + 22.5) // 45 + 1)

    @property
    def distance(self) -> float:
        if self.is_draw_gpu:
            return (self.last_window_position - self.event_window_position).magnitude
        return False

    @property
    def direction_element(self):  # 当前方向上的元素;
        return self.direction_items.get(str(self.direction), None)

    @property
    def direction_items(self):
        def get_direction(item):
            element = item.trajectory_tree.last_element
            og = item.operator_gesture
            if element:
                return element.gesture_direction_items
            elif og:
                return og.gesture_direction_items
            else:
                return {}

        items = get_direction(self)
        if not len(items):
            self.gesture_direction_cache_clear()
            return get_direction(self)
        else:
            return items

    @property
    def is_draw_gpu(self) -> bool:
        context_screen = self.screen
        screen_ok = bpy.context.screen == context_screen
        is_ok = self.trajectory_tree.last_point is not None
        return is_ok and screen_ok

    @property
    def is_window_region_type(self):
        return bpy.context.region.type == 'WINDOW'

    @property
    def is_beyond_threshold(self):
        return self.distance > self.gesture_property.threshold

    @property
    def is_beyond_threshold_confirm(self):
        gesture_property = self.gesture_property
        return self.distance > (gesture_property.threshold_confirm + gesture_property.threshold)

    @property
    def is_access_child_gesture(self):  # 是可以进入子手势的
        element = self.direction_element
        return self.is_beyond_threshold_confirm and element and element.is_child_gesture

    @property
    def operator_time(self):
        move_time = self.first_mouse_move_time
        if move_time:
            return time.time() - self.first_mouse_move_time

    @property
    def is_draw_gesture(self):
        if self.draw_trajectory_mouse_move:
            return self.draw_trajectory_mouse_move
        operator_time = self.operator_time
        if not operator_time:
            return False
        is_timeout = operator_time > (self.pref.gesture_property.timeout / 1000)
        if is_timeout:
            self.draw_trajectory_mouse_move = True
        return is_timeout

    @property
    def find_closest_point(self):
        tree = self.trajectory_tree.kd_tree
        tree.balance()
        return tree.find((*self.event_window_position, 0))

    @property
    def first_mouse_move_time(self) -> float:
        move_time = self.trajectory_mouse_move_time
        if len(move_time):
            return move_time[-1]
