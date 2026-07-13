import bpy
from bpy.props import StringProperty
from mathutils import Vector

from .draw_gpu import DrawGpu
from ...gesture import GestureProperty
from ...gesture.gesture_draw_gpu import GestureGpuDraw
from ...gesture.gesture_handle import GestureHandle
from ...utils.public import PublicOperator, debug_print
from ...utils.session_state import SessionState


class GesturePreview(PublicOperator, GestureHandle, GestureGpuDraw, GestureProperty):
    bl_idname = "wm.gesture_preview"
    bl_label = "Gesture preview"
    bl_description = "Preview gesture layout and directions without running operators"

    gesture: StringProperty()

    offset = Vector([300, 0])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.points_list = None
        self.mouse_position = None
        self.__difference_mouse__ = None

        self.start_mouse_position = None
        self.offset_position = Vector((0, 0))

        self.gpu = DrawGpu()

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

    @property
    def is_draw_gesture(self) -> bool:
        """Return whether to draw gesture preview."""
        if self.draw_trajectory_mouse_move:
            return True
        return self.last_move_mouse_timeout

    def __sync_gesture__(self):
        """Sync gesture name from preview."""
        ag = self.pref.active_gesture
        if ag and self.gesture != ag.name:
            self.gesture = ag.name
            tree = self.trajectory_tree
            if len(tree) >= 2:
                debug_print(tree, key='modal')

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.area = context.area
        self.screen = context.screen
        self.init_invoke(event)

        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.offset_position = self.start_mouse_position

        self.init_trajectory()
        self._schedule_gesture_timeout_timer()
        self._ensure_trajectory_seed()
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
        """Handle Space-drag to move the preview UI, and Esc to cancel."""
        space = (event.type == "SPACE" and not event.alt and not event.ctrl and not event.shift)
        mv = (event.type == "MOUSEMOVE" and event.type_prev == "SPACE")
        if space or mv:
            if event.value == "PRESS":
                self.__difference_mouse__ = self.start_mouse_position - self.mouse_position
                self.points_list = self.trajectory_tree.points_list
            elif event.value == "RELEASE":
                nd = self.start_mouse_position - self.mouse_position
                diff = self.__difference_mouse__ - nd

                self.trajectory_tree.points_list = [pos + diff for pos in self.points_list]
                self.points_list = None
                self.__difference_mouse__ = None
            elif self.__difference_mouse__:
                nd = self.start_mouse_position - self.mouse_position
                diff = self.__difference_mouse__ - nd
                self.offset_position = self.mouse_position - diff

                self.trajectory_tree.points_list = [pos + diff for pos in self.points_list]

            return {'PASS_THROUGH', 'RUNNING_MODAL'}
        if self.is_exit:
            self.__exit_modal__()
            return {'FINISHED'}

    def __exit_modal__(self):
        SessionState.gesture_preview_active = False
        self.unregister_draw()
        self._cancel_gesture_timeout_timer()

        window = getattr(bpy.context, 'window', None)
        if window is not None and window.screen is not None:
            for area in window.screen.areas:
                area.tag_redraw()
