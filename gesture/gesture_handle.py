import time

import bpy
from bpy.props import IntProperty, BoolProperty

from ..gesture.gesture_point_kd_tree import GesturePointKDTree


class GestureHandle:
    trajectory_mouse_move: []  # 鼠标移动轨迹,在每次移动鼠标时就加上
    trajectory_mouse_move_time: []  # 鼠标移动时间
    trajectory_tree: 'GesturePointKDTree'  # 轨迹树
    event_count: IntProperty()
    draw_trajectory_mouse_move: BoolProperty(options={'SKIP_SAVE'})

    def check_return_previous(self):
        point, index, distance = self.find_closest_point
        points_kd_tree = self.trajectory_tree
        if (distance < 10) and (index + 1 != len(points_kd_tree.child_element)):
            points_kd_tree.remove(index)
            self.gesture_direction_cache_clear()

    def try_running_operator(self):
        element = self.direction_element
        if self.is_beyond_threshold_confirm and element and element.is_operator:
            element.running_operator()
            return True

    def init_invoke(self, event):
        self.event_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.trajectory_tree = GesturePointKDTree()
        self.draw_trajectory_mouse_move = False
        return super().init_invoke(event)

    def init_module(self, event):
        self.event_count += 1
        emp = self.event_window_position
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
            self.check_return_previous()
        return super().init_module(event)

    def update_modal(self, context, event):
        self.register_draw()
        self.area = context.area
        self.screen = bpy.context.screen
        self.init_module(event)
        self.tag_redraw()
