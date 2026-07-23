import bpy
from bpy.props import StringProperty
from mathutils import Vector

from .draw_gpu import DrawGpu
from ...gesture.gesture_draw_gpu import GestureGpuDraw
from ...gesture.gesture_handle import GestureHandle
from ...gesture.gesture_input import refresh_snapshot
from ...gesture.preview_input import PreviewGestureInputProcessor
from ...gesture.gesture_runtime import GestureRuntimeMixin
from ...gesture.gesture_session import GestureSession
from ...utils.adapter import operator_setattr
from ...utils.public import PublicOperator
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
        operator_setattr(self, "_input_processor", PreviewGestureInputProcessor())
        operator_setattr(self, "_preview_cleaned", False)

    def __gpu_draw__(self):
        self.gpu.tips.__gpu_draw__()
        self.gpu.gesture_bpu.__gpu_draw__()
        super().__gpu_draw__()

    @classmethod
    def poll(cls, context):
        if SessionState.gesture_preview_active:
            cls.poll_message_set("Gesture preview is already running")
            return False
        try:
            from ...utils.public import get_pref

            active = get_pref().active_gesture
        except (KeyError, AttributeError, ReferenceError, RuntimeError):
            active = None
        try:
            is_radial = active is not None and active.gesture_type == 'RADIAL'
        except (AttributeError, ReferenceError, RuntimeError):
            is_radial = False
        if not is_radial:
            cls.poll_message_set("Select a radial gesture to preview")
            return False
        area = getattr(context, 'area', None)
        if (area is None or area.type != 'VIEW_3D') and cls.find_view3d_context(context) is None:
            cls.poll_message_set("Open a 3D View to preview this gesture")
            return False
        return True

    @staticmethod
    def find_view3d_context(context) -> dict | None:
        """Return a safe VIEW_3D WINDOW override for Preferences launches."""
        wm = getattr(context, 'window_manager', None)
        if wm is None:
            return None
        current_window = getattr(context, 'window', None)
        try:
            windows = list(wm.windows)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        if current_window in windows:
            windows.remove(current_window)
            windows.insert(0, current_window)
        for window in windows:
            try:
                screen = window.screen
                areas = screen.areas
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                continue
            for area in areas:
                if area.type != 'VIEW_3D':
                    continue
                region = next((item for item in area.regions if item.type == 'WINDOW'), None)
                if region is None:
                    continue
                return {
                    'window': window,
                    'area': area,
                    'region': region,
                }
        return None

    @property
    def is_exit(self):
        # ESC always exits. Right-click exits only inside the 3D View window
        # region — right-clicking UI (N panel, menus) must keep the preview
        # alive so "Add to Gesture" works while previewing.
        event = self.event
        if event.type == 'ESC' and event.value == 'PRESS':
            return True
        return self.is_right_mouse and self._mouse_in_window_region(event)

    def _mouse_in_window_region(self, event) -> bool:
        area = self.session.area
        if area is None:
            return True
        from ...utils.region_mouse import find_window_region
        try:
            region = find_window_region(area)
        except ReferenceError:
            return True
        if region is None:
            return True
        return (
            region.x <= event.mouse_x <= region.x + region.width
            and region.y <= event.mouse_y <= region.y + region.height
        )

    def __sync_gesture__(self) -> bool:
        """Rebuild when the active radial changes; reject non-radial data.

        Only updating the name would keep the old gesture's child levels,
        hover stack, and item memos alive in the trajectory tree.
        """
        try:
            ag = self.pref.active_gesture
        except (AttributeError, ReferenceError, RuntimeError):
            return False
        if ag is None or ag.gesture_type != 'RADIAL':
            return False
        if self.gesture != ag.name:
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
        return True

    def _preview_anchor(self, context, event) -> Vector:
        """Always anchor the preview at the 3D View center.

        A centered radial leaves room for panels on every side and matches
        what the gesture looks like in normal use; Space-drag still moves it.
        """
        from ...utils.region_mouse import find_window_region
        region = find_window_region(context.area)
        if region is None:
            return Vector((event.mouse_x, event.mouse_y))
        return Vector((region.x + region.width * 0.5, region.y + region.height * 0.5))

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        import time
        try:
            active = self.pref.active_gesture
        except (AttributeError, ReferenceError, RuntimeError):
            active = None
        try:
            is_radial = active is not None and active.gesture_type == 'RADIAL'
        except (AttributeError, ReferenceError, RuntimeError):
            is_radial = False
        if not is_radial:
            self.report({'WARNING'}, "Only radial gestures can be previewed")
            return {'CANCELLED'}
        self.gesture = active.name

        area = getattr(context, 'area', None)
        if area is None or area.type != 'VIEW_3D':
            override = self.find_view3d_context(context)
            if override is None:
                self.report({'WARNING'}, "Open a 3D View to preview this gesture")
                return {'CANCELLED'}
            try:
                with context.temp_override(**override):
                    result = bpy.ops.wm.gesture_preview(
                        'INVOKE_DEFAULT', gesture=self.gesture,
                    )
            except (AttributeError, RuntimeError, TypeError):
                self.report({'WARNING'}, "Unable to start the preview in the 3D View")
                return {'CANCELLED'}
            # The redirected instance owns the modal handler; this Preferences
            # instance must finish immediately.
            operator_setattr(self, "_preview_cleaned", True)
            return {'FINISHED'} if result and 'RUNNING_MODAL' in result else result

        operator_setattr(self, "_preview_cleaned", False)
        self.init_invoke(event)
        self.session.reset(event, context.area, context.screen, self.gesture)

        anchor = self._preview_anchor(context, event)
        self.start_mouse_position = anchor.copy()
        self.offset_position = anchor.copy()
        self.session._gesture_circle_center = anchor.copy()
        self.session._last_trajectory_mouse = anchor.copy()
        self.trajectory_tree.append(None, anchor.copy())
        self.trajectory_mouse_move.append(anchor.copy())
        self.trajectory_mouse_move_time.append(time.time())

        self._schedule_gesture_timeout_timer()
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
        if not self.__sync_gesture__():
            self.__exit_modal__()
            return {'FINISHED'}

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

    def _apply_trajectory_drag(self, diff: Vector) -> None:
        """Translate trajectory + radial center together (KD-tree rebuilt)."""
        self.trajectory_tree.set_points(pos + diff for pos in self.points_list)
        last = self.trajectory_tree.last_point
        if last is not None:
            self.session._gesture_circle_center = last.copy()
            self.session._last_trajectory_mouse = last.copy()

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

                self._apply_trajectory_drag(diff)
                self.points_list = None
                self.__difference_mouse__ = None
            elif self.__difference_mouse__:
                nd = self.start_mouse_position - self.mouse_position
                diff = self.__difference_mouse__ - nd
                self.offset_position = self.mouse_position - diff

                self._apply_trajectory_drag(diff)

            return {'PASS_THROUGH', 'RUNNING_MODAL'}
        if self.is_exit:
            self.__exit_modal__()
            return {'FINISHED'}

    def __exit_modal__(self):
        if getattr(self, '_preview_cleaned', False):
            return
        operator_setattr(self, "_preview_cleaned", True)
        SessionState.gesture_preview_active = False
        self.unregister_draw()
        self._cancel_gesture_timeout_timer()
        from ...gesture.gesture_input import clear_gesture_item_memos
        clear_gesture_item_memos(self.session, self)

        window = getattr(bpy.context, 'window', None)
        if window is not None and window.screen is not None:
            for area in window.screen.areas:
                area.tag_redraw()
