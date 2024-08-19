import math
import time

import bpy
from bpy.props import IntProperty, BoolProperty, StringProperty
from mathutils import Vector

from ..utils.public import PublicProperty
from ..utils.public_cache import cache_update_lock


class GestureProperty(PublicProperty):
    timer = None

    @cache_update_lock
    def copy(self) -> None:
        """复制一个手势"""
        from ..utils import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self)
        PropertySetUtils.set_prop(self.pref, 'gesture', {'0': copy_data})

    def update_index(self, _) -> None:
        """更新索引"""
        try:
            el = self.element.values()[self.index_element]
            if el:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='索引', update=update_index)

    enabled: BoolProperty(
        default=True,
        update=lambda self, context: self.key_update()
    )

    @property
    def is_active(self) -> bool:
        """此手势是活动项"""
        return self.pref.active_gesture == self

    @property
    def __mouse_position__(self) -> Vector:
        """mouse position"""
        return Vector((self.event.mouse_x, self.event.mouse_y))

    @property
    def __last_window_position__(self) -> Vector:
        """最后一个鼠标位置"""
        return self.trajectory_tree.last_point

    @property
    def __last_region_position__(self) -> Vector:
        """最后一个区域位置"""
        region = bpy.context.region
        if self.is_draw_gpu:
            x, y = self.__last_window_position__
            return Vector(((x - region.x), (y - region.y)))
        return False

    @property
    def operator_gesture(self) -> 'GestureProperty':
        """
        当前操作符执行的手势
        :return:
        """
        return self.pref.gesture.get(self.gesture)

    @property
    def angle(self) -> float:  # 角度
        """当前手势的角度"""
        if self.is_draw_gpu:
            vector = self.__last_window_position__ - self.__mouse_position__
            if vector == Vector((0, 0)):
                return False  # not move mouse
            angle = (180 * vector.angle_signed(Vector((-1, 0)), Vector((0, 0)))) / math.pi
            return angle
        return False

    @property
    def angle_unsigned(self) -> float:
        """当前手势角度无符号"""
        angle = self.angle
        if angle is not None:
            aa = abs(angle)
            if aa == angle:
                return angle
            else:
                return 360 + angle

    @property
    def direction(self) -> int:
        """当前手势方向"""
        angle = self.angle_unsigned
        if angle is bool:
            return False
        if angle > 337.5:
            return 1
        return int((angle + 22.5) // 45 + 1)

    @property
    def distance(self) -> float:
        """当前手势距离"""
        if self.is_draw_gpu:
            return (self.__last_window_position__ - self.__mouse_position__).magnitude
        return False

    @property
    def direction_element(self) -> 'GestureElement':
        """当前方向上的元素"""
        return self.direction_items.get(str(self.direction), None)

    @property
    def direction_items(self) -> dict[str, 'GestureElement']:
        """
        方向上的元素 8个，如果有重复的会取后面的
        :return:
        """

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
        """是绘制gpu的
        判断是否有屏幕
        轨迹数是否有最后一个点
        """
        context_screen = self.screen
        screen_ok = bpy.context.screen == context_screen
        is_ok = self.trajectory_tree.last_point is not None
        return is_ok and screen_ok

    @property
    def is_window_region_type(self) -> bool:
        """判断区域是否是WINDOW类型"""
        return bpy.context.region.type == 'WINDOW'

    @property
    def is_beyond_threshold(self) -> bool:
        """手势距离是否超出阈值"""
        return self.distance > self.gesture_property.threshold

    @property
    def is_beyond_threshold_confirm(self) -> bool:
        """手势距离超出是否超出阈值确定"""
        gesture_property = self.gesture_property
        return self.distance > (gesture_property.threshold_confirm + gesture_property.threshold)

    @property
    def is_access_child_gesture(self) -> bool:
        """是可以进入子手势的"""
        element = self.direction_element
        return self.is_beyond_threshold_confirm and element and element.is_child_gesture

    @property
    def operator_time(self) -> float:
        """操作符时间"""
        move_time = self.first_mouse_move_time
        if move_time:
            return time.time() - self.first_mouse_move_time

    @property
    def is_draw_gesture(self) -> bool:
        """是否绘制手势的布尔值"""
        if self.draw_trajectory_mouse_move:
            return True
        operator_time = self.operator_time
        if not operator_time:
            # 没有操作符时间
            return False
        is_timeout = operator_time > (self.pref.gesture_property.timeout / 1000)
        if is_timeout:
            # 是超时
            self.draw_trajectory_mouse_move = True
        return is_timeout

    @property
    def find_closest_point(self) -> [Vector, int, float]:
        """
        找到最近的点
        https://docs.blender.org/api/master/mathutils.kdtree.html#mathutils.kdtree.KDTree.find
        :return: (Vector, index, distance)
        """
        tree = self.trajectory_tree.kd_tree
        tree.balance()
        return tree.find((*self.__mouse_position__, 0))

    @property
    def first_mouse_move_time(self) -> float:
        """
        鼠标第一次移动的时间
        :return:
        """
        move_time = self.trajectory_mouse_move_time
        if len(move_time):
            return move_time[-1]
