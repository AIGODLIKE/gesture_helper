import time

import bpy

from ..gesture.gesture_point_kd_tree import GesturePointKDTree


class GestureHandle:
    trajectory_mouse_move: []  # Mouse move trajectory points
    trajectory_mouse_move_time: []  # Mouse move timestamps
    trajectory_tree: "GesturePointKDTree"  # Trajectory KD-tree
    event_count: 0  # Event counter
    draw_trajectory_mouse_move: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.screen = None
        self.area = None
        self._gesture_timeout_timer = None

    def _tag_redraw_gesture_screen(self):
        """Redraw the screen that started this gesture (timer may have wrong context)."""
        screen = getattr(self, 'screen', None)
        if screen is not None:
            try:
                for area in screen.areas:
                    area.tag_redraw()
                return
            except ReferenceError:
                ...
        from ..utils.public import tag_redraw
        tag_redraw()

    def tag_redraw(self):
        self._tag_redraw_gesture_screen()

    def _ensure_trajectory_seed(self):
        """Ensure GPU draw has an anchor point before the first mouse move."""
        tree = getattr(self, 'trajectory_tree', None)
        if tree is None or len(tree):
            return
        try:
            tree.append(None, self.__mouse_position__)
        except (AttributeError, ReferenceError, TypeError):
            ...

    def _cancel_gesture_timeout_timer(self):
        timer = getattr(self, '_gesture_timeout_timer', None)
        if timer is None:
            return
        try:
            bpy.app.timers.unregister(timer)
        except ValueError:
            ...
        self._gesture_timeout_timer = None

    def _schedule_gesture_timeout_timer(self):
        self._cancel_gesture_timeout_timer()
        if getattr(self, 'draw_trajectory_mouse_move', False):
            return
        timeout = self.pref.gesture_property.timeout / 1000
        if timeout <= 0:
            return

        def _on_timeout(*_args):
            self._gesture_timeout_timer = None
            try:
                self.draw_trajectory_mouse_move = True
                self._ensure_trajectory_seed()
                self._tag_redraw_gesture_screen()
            except (AttributeError, ReferenceError):
                ...
            return None

        self._gesture_timeout_timer = _on_timeout
        bpy.app.timers.register(_on_timeout, first_interval=timeout)

    def check_return_previous(self):
        """Check returning to a previous gesture point."""
        point, index, distance = self.find_closest_point
        points_kd_tree = self.trajectory_tree
        scale = bpy.context.preferences.view.ui_scale
        return_distance = self.gesture_property.return_distance * scale
        if (distance < return_distance) and (index + 1 != len(points_kd_tree.child_element)):
            points_kd_tree.remove(index)
            self.invalidate_derived_caches(force=True)

    def _derived_invalidation_key(self):
        """Cache key for derived direction/extension data."""
        return self._direction_items_context_id()

    def invalidate_derived_caches(self, *, force=False):
        """Clear direction/extension caches only when modal context actually changed."""
        key = self._derived_invalidation_key()
        if not force and getattr(self, '_derived_cache_key', None) == key:
            return
        self._derived_cache_key = key
        self._direction_items_memo = None
        self._gpu_extension_items_cache = None
        self.gesture_direction_cache_clear()
        self.gesture_extension_cache_clear()

    def try_running_operator(self, ops):
        """Try to run gesture operator(s)."""

        def run(i):
            from bpy.app.translations import pgettext_iface
            from .gesture_pass_through_keymap import (
                defer_gesture_element_operator,
                should_defer_gesture_operator,
            )
            from ..element.element_operator import resolve_operator_bl_idname

            if i.operator_is_operator or i.operator_is_modal:
                if i.operator_func is None:
                    gesture_name = pgettext_iface(self.operator_gesture.name)
                    tips = pgettext_iface(
                        "Operator not found, please check the operator id in gesture settings")
                    ops.report(
                        {'ERROR'},
                        f"{tips} {gesture_name} -> {i.name_translate} bpy.ops.{i.operator_bl_idname}",
                    )
                    return

            if i.check_operator_poll():
                idname = resolve_operator_bl_idname(i.operator_bl_idname)
                # Opening Preferences / menus while still modal leaves the gesture stuck.
                if i.operator_is_operator and should_defer_gesture_operator(idname):
                    area = getattr(self, 'area', None) or getattr(ops, 'area', None)
                    if defer_gesture_element_operator(bpy.context, area, i):
                        ops.report({'INFO'}, i.name_translate)
                        return
                error = i.running_operator()
                if error is not None:
                    ops.report({'ERROR'}, pgettext_iface("Operator Run Error,Please check the console"))
                    return
                ops.report({'INFO'}, i.name_translate)
            else:
                gesture_name = pgettext_iface(self.operator_gesture.name)
                tips = pgettext_iface(
                    "Operator context error, please ensure that the operator is available in this context")
                ops.report(
                    {'ERROR'},
                    f"{tips} {gesture_name} -> {i.name_translate} bpy.ops.{i.operator_bl_idname}.poll()",
                )

        # Run extension menu operators
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
        """Initialize trajectory state."""
        self.event_count = 1
        self.move_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.trajectory_tree = GesturePointKDTree()
        self.draw_trajectory_mouse_move = False
        self.last_mouse_mouse_time = time.time()
        self._derived_cache_key = None
        self._direction_items_memo = None

    def trajectory_event_update(self, context, event):
        """Update trajectory from modal event."""
        self.area = context.area
        self.screen = context.screen
        if event.type != "TIMER":
            self.move_count += 1
        if event.type == "MOUSEMOVE":
            self.last_mouse_mouse_time = time.time()
            self._schedule_gesture_timeout_timer()
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
                        self.invalidate_derived_caches()
                else:
                    self.trajectory_tree.append(self.direction_element, emp)
                    self.invalidate_derived_caches()
            if self.is_draw_gesture:
                self.check_return_previous()
        self.tag_redraw()

    @property
    def is_have_extension_item(self) -> bool:
        return self.is_draw_gesture and "9" in self._raw_direction_items_dict()
