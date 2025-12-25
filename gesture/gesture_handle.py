import time

import bpy

from ..gesture.gesture_point_kd_tree import GesturePointKDTree


class GestureHandle:
    trajectory_mouse_move: []  # 鼠标移动轨迹,在每次移动鼠标时就加上
    trajectory_mouse_move_time: []  # 鼠标移动时间
    trajectory_tree: "GesturePointKDTree"  # 轨迹树
    event_count: 0  # 事件数
    draw_trajectory_mouse_move: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            self.gesture_extension_cache_clear()

    def try_running_operator(self, ops):
        """尝试运行手势"""

        def run(i):
            if i.check_operator_poll():
                error = i.running_operator()
                if error is not None:
                    from bpy.app.translations import pgettext_iface
                    ops.report({'ERROR'}, pgettext_iface("Operator Run Error,Please check the console"))
                    return
                ops.report({'INFO'}, i.name_translate)
            else:
                name = bpy.app.translations.pgettext_iface(self.operator_gesture.name)
                tips = bpy.app.translations.pgettext_iface(
                    "Operator context error, please ensure that the operator is available in this context")
                self.report({'ERROR'},
                            f" {tips} {name}->{i.name} bpy.ops.{i.operator_bl_idname}.poll()")
                # poll失败

        # 运行扩展的操作符
        if self.extension_element and len(self.extension_hover):
            last = self.extension_hover[-1]
            for item in last.extension_items:
                if item.extension_by_child_is_hover and item.is_operator:
                    run(item)
                    return True

        element = self.direction_element
        if element and element.is_operator and (self.is_beyond_threshold_confirm or element.mouse_is_in_area):
            run(element)
            return True
        return False

    def init_trajectory(self):
        """初始化轨迹信息"""
        self.event_count = 1
        self.move_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.trajectory_tree = GesturePointKDTree()
        self.draw_trajectory_mouse_move = False
        self.last_mouse_mouse_time = time.time()

    def trajectory_event_update(self, context, event):
        """事件轨迹"""
        self.area = context.area
        self.screen = context.screen
        if event.type != "TIMER":
            self.move_count += 1
        if event.type == "MOUSEMOVE":
            self.last_mouse_mouse_time = time.time()
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

                if self.is_have_extension_item and self.direction_element.direction == "7":
                    if self.last_move_mouse_timeout and not self.is_beyond_extension_offset_distance:
                        self.trajectory_tree.append(self.direction_element, emp)
                        self.gesture_direction_cache_clear()
                        self.gesture_extension_cache_clear()
                else:
                    self.trajectory_tree.append(self.direction_element, emp)
                    self.gesture_direction_cache_clear()
                    self.gesture_extension_cache_clear()
            if self.is_draw_gesture:
                self.check_return_previous()
        self.tag_redraw()

    @property
    def is_have_extension_item(self) -> bool:
        return self.is_draw_gesture and "9" in self.direction_items
