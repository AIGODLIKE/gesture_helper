# Display operator — thin orchestration over Session / Input / Execute / Draw

import bpy
from bpy.app.translations import pgettext_iface
from bpy.props import StringProperty

from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..gesture.gesture_executor import GestureExecutor
from ..gesture.gesture_handle import GestureHandle
from ..gesture.gesture_input import (
    GestureInputProcessor,
    ensure_trajectory_seed,
    refresh_snapshot,
    schedule_timeout_timer,
)
from ..gesture.gesture_runtime import GestureRuntimeMixin
from ..gesture.gesture_session import GestureSession
from ..gesture.pass_through import GesturePassThroughKeymap
from ..utils.public import PublicOperator, debug_print


class GestureOperator(
    PublicOperator,
    GestureHandle,
    GestureGpuDraw,
    GestureRuntimeMixin,
    GesturePassThroughKeymap,
):
    bl_idname = 'wm.gesture_operator'
    bl_label = 'Gesture Operator'
    bl_description = 'Run the active gesture from its keymap shortcut'
    bl_options = {'BLOCKING'}
    # Must use annotation form — Blender reads bpy.props from __annotations__.
    gesture: StringProperty()

    @classmethod
    def poll(cls, context):
        from ..utils.pref import poll_addon_preferences
        return poll_addon_preferences(cls)

    def __init__(self, *args, **kwargs):
        # Blender 5.x: call Operator __init__ first, then attach plain Python
        # state via object.__setattr__ (RNA __setattr__ rejects unknown attrs).
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "session", GestureSession())
        object.__setattr__(self, "_input", GestureInputProcessor())
        object.__setattr__(self, "_executor", GestureExecutor())

    def tag_redraw(self):
        """Redraw the gesture screen (override PublicOperator.tag_redraw)."""
        self._tag_redraw_gesture_screen()

    def draw_error(self, __):
        layout = self.layout
        for text in [
            "No gesture found to draw",
            "Possible errors in keymap",
            "Please go to the add-on preferences to restore keymap",
        ]:
            layout.label(text=text)

    def invoke(self, context, event):
        if pass_d := self.try_pass_annotations_eraser(context, event):
            return pass_d
        if pass_right_mouse := self.try_pass_paint_texture_stencil(context, event):
            return pass_right_mouse

        # Preferences / other utility windows must not start a gesture modal —
        # opening prefs from a gesture while already in prefs breaks focus.
        area = context.area
        if area is not None and area.type in {'PREFERENCES', 'FILE_BROWSER'}:
            return {'CANCELLED'}

        self.init_invoke(event)
        self.session.reset(event, context.area, context.screen, self.gesture)
        if self.operator_gesture is None:
            context.window_manager.popup_menu(self.__class__.draw_error,
                                              title=pgettext_iface("Error"),
                                              icon="INFO")
            return {'CANCELLED'}

        # Rebuild structure cache before the first snapshot so direction walks
        # see a consistent generation (avoid clear-after-refresh stale memo).
        self.cache_clear()
        ensure_trajectory_seed(self.session)
        refresh_snapshot(self.session, self)
        schedule_timeout_timer(self.session, self.pref.gesture_property.timeout, self)
        self.register_draw()

        debug_print(
            "invoke", self.bl_idname,
            f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev,
            key='modal',
        )

        wm = context.window_manager
        wm.modal_handler_add(self)
        debug_print(self.bl_idname, event.type, event.value, key='modal')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Focus left this window (e.g. Preferences popup took focus): cancel
        # cleanly without running gesture operators — avoids focus fights.
        if event.type == 'WINDOW_DEACTIVATE':
            # While sync-opening Preferences (or other deferred UI), ignore
            # deactivate so exit() can still return FINISHED+INTERFACE.
            if self.session.handoff.ignore_window_deactivate:
                return {'RUNNING_MODAL'}
            self.__exit_modal__()
            return {'CANCELLED'}

        self.init_modal(event)
        dirty = self._input.on_event(self.session, self, event)
        if dirty:
            self.tag_redraw()

        debug_print(
            self.bl_idname, f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev, key='modal',
        )
        if self._executor.try_immediate_implementation(self.session, self):
            self.__exit_modal__()
            if self.session.handoff.needs_interface:
                return {'FINISHED', 'INTERFACE'}
            return {"FINISHED"}
        if self.is_exit:
            self.__exit_modal__()
            return self.exit(context, event)
        return {'RUNNING_MODAL'}

    def exit(self, context: bpy.types.Context, event: bpy.types.Event):
        # Refresh snapshot once more with the release event before dispatch.
        self.session.event = event
        self.event = event
        refresh_snapshot(self.session, self)
        from ..gesture.gesture_input import update_extension_hover
        update_extension_hover(self.session, self)

        ops = self._executor.try_running_operator(self.session, self)

        if self.is_debug:
            debug_print('ops', ops, key='modal')
            debug_print(
                self.session.phase, self.session.snapshot.threshold_zone,
                self.is_draw_gpu, self.session.handoff,
                key='modal',
            )

        if not ops:
            # Pass gate (drawn/timeout/drag → no pass) lives in
            # GesturePassThroughKeymap.can_pass_through_keymap — do not add
            # RMB exceptions here.
            if self.is_debug:
                area = getattr(self, 'area', None) or context.area
                view_type = getattr(context.space_data, "view_type", None)
                view = getattr(context.space_data, "view", None)
                mode = getattr(context.space_data, "mode", None)
                region = getattr(bpy.context, 'region', None)
                region_type = region.type if region is not None else None
                debug_print(
                    f'PASS_THROUGH EVENT\tTYPE:{self.event.type}\t\tVALUE:{self.event.value}',
                    key='modal',
                )
                debug_print(
                    f"Context Mode:{context.mode}\tAREA:{getattr(area, 'type', None)}\tREGION:{region_type}",
                    key='modal',
                )
                debug_print(
                    f"SPACE_DATA\tview_type:{view_type}\tview:{view}\tmode:{mode}",
                    key='modal',
                )
            if self.try_pass_through_keymap(context, event) == 'handled':
                return {'FINISHED', 'INTERFACE'}
        if self.session.handoff.needs_interface:
            return {'FINISHED', 'INTERFACE'}
        return {'FINISHED'}

    def cancel(self, context):
        self.__exit_modal__()

    def __exit_modal__(self):
        self.unregister_draw()
        self._cancel_gesture_timeout_timer()
        # Keep session.handoff until invoke reset — exit()/immediate still read it
        # after __exit_modal__ to decide FINISHED+INTERFACE.

    @property
    def mouse_is_in_extension_any_area(self) -> bool:
        if self.extension_element and self.extension_hover:
            for last in self.extension_hover:
                if (
                        last.extension_by_child_is_hover or
                        last.mouse_is_in_extension_area or
                        last.mouse_is_in_extension_vertical_outside_area or
                        last.mouse_is_in_extension_right_outside_area
                ):
                    return True

                for item in last.extension_items:
                    if (
                            item.extension_by_child_is_hover or
                            item.mouse_is_in_extension_area or
                            item.mouse_is_in_extension_vertical_outside_area or
                            item.mouse_is_in_extension_right_outside_area
                    ):
                        return True
        return False
