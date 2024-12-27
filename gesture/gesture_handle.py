import time

import bpy
from bpy.props import IntProperty, BoolProperty

from ..gesture.gesture_point_kd_tree import GesturePointKDTree


class GestureHandle:
    trajectory_mouse_move: []  # 鼠标移动轨迹,在每次移动鼠标时就加上
    trajectory_mouse_move_time: []  # 鼠标移动时间
    trajectory_tree: "GesturePointKDTree"  # 轨迹树
    event_count: IntProperty(options={"SKIP_SAVE", "HIDDEN"})  # 事件数
    draw_trajectory_mouse_move: BoolProperty(options={"SKIP_SAVE", "HIDDEN"})

    def __init__(self):
        self.screen = None
        self.area = None

    def check_return_previous(self):
        """检查回到之前的手势"""
        point, index, distance = self.find_closest_point
        points_kd_tree = self.trajectory_tree
        scale = bpy.context.preferences.view.ui_scale
        return_distance = self.gesture_property.return_distance * scale
        if (distance < return_distance) and (index + 1 != len(points_kd_tree.child_element)):
            points_kd_tree.remove(index)
            self.gesture_direction_cache_clear()

    def try_running_operator(self, ops):
        """尝试运行手势"""
        element = self.direction_element
        if self.is_beyond_threshold_confirm and element and element.is_operator:
            error = element.running_operator()
            if error is not None:
                from bpy.app.translations import pgettext_iface
                ops.report({'ERROR'}, pgettext_iface("Operator Run Error,Please check the console"))
            return True

    def init_trajectory(self):
        """初始化轨迹信息"""
        self.event_count = 1
        self.move_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.trajectory_tree = GesturePointKDTree()
        self.draw_trajectory_mouse_move = False

    def event_trajectory(self, context, event):
        """事件轨迹"""
        self.area = context.area
        self.screen = context.screen
        if event.type != "TIMER":
            self.move_count += 1
        self.event_count += 1
        emp = self.__mouse_position__
        if self.event_count > 2:
            not_draw = not self.is_draw_gesture
            if (not len(self.trajectory_mouse_move) or self.trajectory_mouse_move[-1] != emp) and not_draw:
                self.trajectory_mouse_move.append(emp)
                self.trajectory_mouse_move_time.append(time.time())
            if not len(self.trajectory_tree):
                self.trajectory_tree.append(None, emp)
            if self.is_access_child_gesture:
                self.trajectory_tree.append(self.direction_element, emp)
                self.gesture_direction_cache_clear()
            if self.is_draw_gesture:
                self.check_return_previous()
        self.tag_redraw()
