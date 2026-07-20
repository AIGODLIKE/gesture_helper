import bpy
from bpy.props import StringProperty
from mathutils import Vector

from .draw_gpu import DrawGpu
from ...gesture.gesture_draw_gpu import GestureGpuDraw
from ...gesture.gesture_handle import GestureHandle
from ...gesture.gesture_input import refresh_snapshot
from ...gesture.gesture_runtime import GestureRuntimeMixin
from ...gesture.gesture_session import GestureSession
from ...utils.adapter import operator_setattr
from ...utils.public import PublicOperator, debug_print
from ...utils.session_state import SessionState


class GesturePreview(PublicOperator, GestureHandle, GestureGpuDraw, GestureRuntimeMixin):
    bl_idname = "wm.gesture_preview"
    bl_label = "Gesture preview"
    bl_description = "Preview gesture layout and directions without running operators"

    # Must use annotation form — Blender reads bpy.props from __annotations__.
    gesture: StringProperty()

    offset = Vector([300, 0])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        operator_setattr(self, "session", GestureSession())
        operator_setattr(self, "points_list", None)
        operator_setattr(self, "mouse_position", None)
        operator_setattr(self, "__difference_mouse__", None)
        operator_setattr(self, "start_mouse_position", None)
        operator_setattr(self, "offset_position", Vector((0, 0)))
        operator_setattr(self, "gpu", DrawGpu())

    def __gpu_draw__(self):
        self.gpu.tips.__gpu_draw__()
        self.gpu.gesture_bpu.__gpu_draw__()
        super().__gpu_draw__()

    @classmethod
    def poll(cls, context):
        if SessionState.gesture_preview_active:
            cls.poll_message_set("Gesture preview is already running")
            return False
        return True

    @property
    def is_exit(self):
        return self.is_right_mouse

    def __sync_gesture__(self):
        """Rebuild the whole preview session when the active gesture changes.

        Only updating the name would keep the old gesture's child levels,
        hover stack, and item memos alive in the trajectory tree.
        """
        ag = self.pref.active_gesture
        if ag and self.gesture != ag.name:
            from ...gesture.gesture_input import clear_gesture_item_memos
            tree = self.trajectory_tree
            center = tree.points_list[0].copy() if tree.points_list else self.offset_position.copy()
            event = self.session.event
            area = self.session.area
            screen = self.session.screen
            self._cancel_gesture_timeout_timer()
            clear_gesture_item_memos(self.session, self)
            self.gesture = ag.name
            self.session.reset(event, area, screen, ag.name)
            self.session._gesture_circle_center = center.copy()
            self.session._last_trajectory_mouse = center.copy()
            self.trajectory_tree.append(None, center)
            self.trajectory_mouse_move.append(center.copy())
            self.trajectory_mouse_move_time.append(0.0)
            self._schedule_gesture_timeout_timer()
            refresh_snapshot(self.session, self)
            self.tag_redraw()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.init_invoke(event)
        self.session.reset(event, context.area, context.screen, self.gesture)

        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.offset_position = self.start_mouse_position

        self._schedule_gesture_timeout_timer()
        self._ensure_trajectory_seed()
        refresh_snapshot(self.session, self)
        self.trajectory_event_update(context, event)
        self.register_draw()

        wm = context.window_manager
        wm.modal_handler_add(self)
        SessionState.gesture_preview_active = True

        self.__sync_gesture__()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.area = context.area
        self.screen = context.screen
        self.__sync_gesture__()

        self.init_modal(event)
        self.trajectory_event_update(context, event)
        self.mouse_position = Vector((event.mouse_x, event.mouse_y))

        res = self.gpu.draw_run(self, event)
        if res:
            if "FINISHED" in res:
                self.__exit_modal__()
            return res
        m = self.modal_event(event)
        if m:
            return m
        return {'PASS_THROUGH'}

    def cancel(self, context):
        self.__exit_modal__()

    def modal_event(self, event):
        """Handle Space-drag to move the preview UI, and right-click to exit."""
        space = (event.type == "SPACE" and not event.alt and not event.ctrl and not event.shift)
        mv = (event.type == "MOUSEMOVE" and event.type_prev == "SPACE")
        if space or mv:
            if event.value == "PRESS":
                self.__difference_mouse__ = self.start_mouse_position - self.mouse_position
                self.points_list = self.trajectory_tree.points_list
            elif event.value == "RELEASE":
                nd = self.start_mouse_position - self.mouse_position
                diff = self.__difference_mouse__ - nd

                self.trajectory_tree.set_points(pos + diff for pos in self.points_list)
                self.points_list = None
                self.__difference_mouse__ = None
            elif self.__difference_mouse__:
                nd = self.start_mouse_position - self.mouse_position
                diff = self.__difference_mouse__ - nd
                self.offset_position = self.mouse_position - diff

                self.trajectory_tree.set_points(pos + diff for pos in self.points_list)

            return {'PASS_THROUGH', 'RUNNING_MODAL'}
        if self.is_exit:
            self.__exit_modal__()
            return {'FINISHED'}

    def __exit_modal__(self):
        SessionState.gesture_preview_active = False
        self.unregister_draw()
        self._cancel_gesture_timeout_timer()
        from ...gesture.gesture_input import clear_gesture_item_memos
        clear_gesture_item_memos(self.session, self)

        window = getattr(bpy.context, 'window', None)
        if window is not None and window.screen is not None:
            for area in window.screen.areas:
                area.tag_redraw()
