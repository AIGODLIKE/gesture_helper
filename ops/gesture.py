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
from ..utils.adapter import operator_setattr
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
        # Call Operator __init__ first (Blender 4.4+), then attach plain Python
        # state. Use operator_setattr — object.__setattr__ fails on 4.x bpy_struct.
        super().__init__(*args, **kwargs)
        operator_setattr(self, "session", GestureSession())
        operator_setattr(self, "_input", GestureInputProcessor())
        operator_setattr(self, "_executor", GestureExecutor())
        operator_setattr(self, "_modal_cleaned", False)

    def tag_redraw(self):
        """Redraw the gesture screen (override PublicOperator.tag_redraw)."""
        self._tag_redraw_gesture_screen()

    def draw_error(self, __):
        layout = self.layout
        for text in [
            "No gesture found to draw",
            "Possible keymap errors",
            "Open add-on preferences to restore the keymap",
        ]:
            layout.label(text=text)

    def invoke(self, context, event):
        if pass_d := self.try_pass_annotations_eraser(context, event):
            return pass_d
        if pass_right_mouse := self.try_pass_paint_texture_stencil(context, event):
            return pass_right_mouse

        # Preferences / other utility windows must not start a gesture modal.
        area = context.area
        if area is not None and area.type in {'PREFERENCES', 'FILE_BROWSER'}:
            return {'CANCELLED'}

        self.init_invoke(event)
        self.session.reset(event, context.area, context.screen, self.gesture)
        operator_setattr(self, "_modal_cleaned", False)
        if self.operator_gesture is None:
            context.window_manager.popup_menu(self.__class__.draw_error,
                                              title=pgettext_iface("Error"),
                                              icon="INFO")
            return {'CANCELLED'}

        # Ensure this gesture's structure cache exists; skip full rebuild when warm.
        from ..utils.public_cache import PublicCacheFunc
        PublicCacheFunc.ensure_gesture_structure(self.operator_gesture)
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

    def _mark_modal_done(self) -> None:
        """Mark this session finished so leftover handler calls force-end."""
        self.session.modal_report_done = True

    def _finish_leftover_modal(self, event) -> set:
        """Blender may keep delivering events after we already returned FINISHED."""
        # Idempotent: draw/timer already torn down on the real exit path.
        self.__exit_modal__()
        return {'FINISHED'}

    def modal(self, context, event):
        """
        Modal state machine (keep this small — focus heuristics belong elsewhere):

        1. ``modal_report_done`` → always FINISHED (zombie-handler guard)
        2. ``WINDOW_DEACTIVATE`` → RUNNING_MODAL (never CANCELLED; is_exit
           already ignores non-invoke RELEASE)
        3. immediate / is_exit → cleanup + exit path
        4. else RUNNING_MODAL
        """
        done = bool(getattr(self.session, 'modal_report_done', False))
        if done:
            return self._finish_leftover_modal(event)

        if event.type == 'WINDOW_DEACTIVATE':
            return {'RUNNING_MODAL'}

        self.init_modal(event)
        dirty = self._input.on_event(self.session, self, event)
        if dirty:
            self.tag_redraw()

        debug_print(
            self.bl_idname, f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev, key='modal',
        )
        if self._executor.try_immediate_implementation(self.session, self):
            # Mark before any further work — immediate already ran the op.
            return self._finish_from_dispatch(context, event, from_immediate=True)
        if self.is_exit:
            # Mark FIRST (before cleanup/ops) so prefs sync cannot re-enter.
            self._mark_modal_done()
            return self._finish_from_dispatch(context, event, from_immediate=False)
        return {'RUNNING_MODAL'}

    def _finish_from_dispatch(self, context, event, *, from_immediate: bool) -> set:
        """Shared finish: mark done early, cleanup, run exit dispatch once."""
        # Mark done BEFORE cleanup/ops so a re-entrant modal call during
        # prefs/window open cannot start a second dispatch on this session.
        self._mark_modal_done()
        self.__exit_modal__()
        if from_immediate:
            # Immediate path already ran the operator inside try_immediate.
            from ..gesture.gesture_input import clear_gesture_item_memos
            clear_gesture_item_memos(self.session, self)
            if self.session.handoff.needs_interface:
                return {'FINISHED', 'INTERFACE'}
            return {'FINISHED'}
        return self.exit(context, event)

    def exit(self, context: bpy.types.Context, event: bpy.types.Event):
        # Refresh snapshot once more with the release event before dispatch.
        self.session.event = event
        self.event = event
        refresh_snapshot(self.session, self)
        from ..gesture.gesture_input import clear_gesture_item_memos, update_extension_hover
        update_extension_hover(self.session, self)

        # Ensure done even if caller forgot (cancel / odd paths).
        self._mark_modal_done()

        ops = False
        try:
            ops = self._executor.try_running_operator(self.session, self)
        finally:
            # Clear after dispatch: extension hit boxes live on cached Element
            # Python proxies; clearing earlier rebuilds fresh proxies without
            # extension_by_child_draw_area and breaks extension execute.
            clear_gesture_item_memos(self.session, self)
            self._mark_modal_done()

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
                ret = {'FINISHED', 'INTERFACE'}
            elif self.session.handoff.needs_interface:
                ret = {'FINISHED', 'INTERFACE'}
            else:
                ret = {'FINISHED'}
        elif self.session.handoff.needs_interface:
            # Deferred menu/panel/search only.
            ret = {'FINISHED', 'INTERFACE'}
        else:
            # Sync operators: plain FINISHED. INTERFACE here can leave the
            # modal handler alive until WINDOW_DEACTIVATE (zombie input).
            ret = {'FINISHED'}
        return ret

    def cancel(self, context):
        # ESC / system cancel: mark done so leftover events cannot resume.
        self._mark_modal_done()
        self.__exit_modal__()
        from ..gesture.gesture_input import clear_gesture_item_memos
        clear_gesture_item_memos(self.session, self)
        return {'CANCELLED'}

    def __exit_modal__(self):
        if getattr(self, "_modal_cleaned", False):
            return
        operator_setattr(self, "_modal_cleaned", True)
        self.unregister_draw()
        self._cancel_gesture_timeout_timer()
        # Do not clear item memos here — exit() still needs draw-area attrs on
        # cached extension Element proxies for try_running_operator.
        # Keep session.handoff until invoke reset — exit()/immediate still read it
        # after __exit_modal__ to decide FINISHED+INTERFACE.

    @property
    def mouse_is_in_extension_any_area(self) -> bool:
        """True when mouse is in extension panel / right band / child row.

        Excludes vertical travel (same subset as GestureExecutor radial block).
        """
        if not self.extension_element or not self.extension_hover:
            return False
        from ..element.extension_hit import stack_any_ui
        return stack_any_ui(self.extension_hover, self, include_vertical_travel=False)
