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
        operator_setattr(self, "_modal_cancelled", False)

    def tag_redraw(self):
        """Redraw the gesture screen (override PublicOperator.tag_redraw)."""
        self._tag_redraw_gesture_screen()

    def draw_error(self, __):
        layout = self.layout
        for text in [
            "Radial gesture not found",
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

        from ..utils.session_state import SessionState

        SessionState.request_gesture_preview_close()

        self.init_invoke(event)
        self.session.reset(event, context.area, context.screen, self.gesture)
        operator_setattr(self, "_modal_cleaned", False)
        operator_setattr(self, "_modal_cancelled", False)
        gesture = self.operator_gesture
        if gesture is None or gesture.gesture_type != 'RADIAL':
            context.window_manager.popup_menu(self.__class__.draw_error,
                                              title=pgettext_iface("Error"),
                                              icon="INFO")
            return {'CANCELLED'}

        # Ensure this gesture's structure cache exists; skip full rebuild when warm.
        from ..utils.public_cache import PublicCacheFunc
        PublicCacheFunc.ensure_gesture_structure(gesture)
        ensure_trajectory_seed(self.session)
        refresh_snapshot(self.session, self)
        try:
            schedule_timeout_timer(
                self.session,
                self.pref.gesture_property.timeout,
                self,
            )
            self.register_draw()
            context.window_manager.modal_handler_add(self)
        except BaseException:
            self._cleanup_modal_after_error()
            raise

        debug_print(
            "invoke", self.bl_idname,
            f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev,
            key='modal',
        )

        debug_print(self.bl_idname, event.type, event.value, key='modal')
        return {'RUNNING_MODAL'}

    def _mark_modal_done(self) -> None:
        """Mark this session finished so leftover handler calls force-end."""
        self.session.modal_report_done = True

    def _finish_leftover_modal(self, event) -> set:
        """Blender may keep delivering events after we already returned FINISHED."""
        # Idempotent: draw/timer already torn down on the real exit path.
        self._input.cancel_property_drag(self.session, self, refresh=False)
        self.__exit_modal__()
        return {'FINISHED'}

    def _cancel_modal(self) -> None:
        """Cancel input, restore an active scrub, and release UI ownership."""
        if getattr(self, "_modal_cancelled", False):
            return
        operator_setattr(self, "_modal_cancelled", True)
        self._mark_modal_done()
        try:
            self._input.cancel_property_drag(self.session, self, refresh=False)
        finally:
            try:
                self.session._suppress_property_execute = False
                self.session.repair_element = None
                self.session.clear_handoff()
            finally:
                try:
                    self.__exit_modal__()
                finally:
                    from ..gesture.gesture_input import clear_gesture_item_memos
                    clear_gesture_item_memos(self.session, self)

    def _cleanup_modal_after_error(self) -> None:
        """Best-effort cleanup without replacing the active exception."""
        try:
            self._cancel_modal()
        except BaseException:
            pass

    def _copy_hover_tooltip(self, context, event) -> bool:
        """Consume Ctrl+C only while a hover tooltip is actually visible."""
        if event.type != 'C' or event.value != 'PRESS' or not event.ctrl:
            return False
        from ..gesture.runtime_tooltip import copy_displayed_tooltip

        if not copy_displayed_tooltip(
                getattr(self.session, 'tooltip_state', None),
                getattr(context, 'window_manager', None),
        ):
            return False
        self.report({'INFO'}, pgettext_iface('Hover information copied'))
        return True

    def modal(self, context, event):
        """
        Modal state machine (keep this small — focus heuristics belong elsewhere):

        1. ``modal_report_done`` → always FINISHED (zombie-handler guard)
        2. ``WINDOW_DEACTIVATE`` → cancel: the key RELEASE may be swallowed
           while the window is unfocused, which would leave a zombie modal
           intercepting input after focus returns
        3. immediate / is_exit → cleanup + exit path
        4. else RUNNING_MODAL
        """
        done = bool(getattr(self.session, 'modal_report_done', False))
        if done:
            return self._finish_leftover_modal(event)

        if event.type == 'WINDOW_DEACTIVATE':
            self._cancel_modal()
            return {'CANCELLED'}

        if event.value == 'PRESS' and event.type in {'ESC', 'RIGHTMOUSE'}:
            self._cancel_modal()
            return {'CANCELLED'}

        if self._copy_hover_tooltip(context, event):
            return {'RUNNING_MODAL'}

        try:
            self.init_modal(event)
            dirty = self._input.on_event(self.session, self, event)
        except BaseException:
            self._cleanup_modal_after_error()
            raise
        if dirty:
            self.tag_redraw()

        repair_element = getattr(self.session, 'repair_element', None)
        if repair_element is not None:
            return self._finish_for_repair(repair_element)

        # A property-row drag consumes its modal event even when integer
        # rounding leaves the value unchanged. Do not let that event fall
        # through to immediate execution or gesture exit checks.
        if getattr(self.session, '_event_consumed', False):
            return {'RUNNING_MODAL'}

        debug_print(
            self.bl_idname, f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev, key='modal',
        )
        try:
            immediate = self._executor.try_immediate_implementation(
                self.session,
                self,
            )
        except BaseException:
            self._cleanup_modal_after_error()
            raise
        if immediate:
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
        # unregister_draw() removes the GPU handler before the final dispatch,
        # so keep the panel pause marker alive until every execute/cleanup path
        # below has finished. Otherwise a redraw can walk Element RNA and
        # replace the hit-box proxies while the release event is still being
        # dispatched.
        self.mark_modal_finishing()
        try:
            self.__exit_modal__()
            if from_immediate:
                # Immediate path already ran the operator inside try_immediate.
                from ..gesture.gesture_input import clear_gesture_item_memos
                clear_gesture_item_memos(self.session, self)
                if self.session.handoff.needs_interface:
                    return {'FINISHED', 'INTERFACE'}
                return {'FINISHED'}
            return self.exit(context, event)
        finally:
            self.clear_modal_finishing()
            from ..utils.ui_draw_sync import (
                cancel_modal_ui_refresh,
                tag_gesture_ui_regions,
            )
            cancel_modal_ui_refresh()
            tag_gesture_ui_regions()

    def _finish_for_repair(self, element) -> set:
        """End the gesture, focus the broken item, then open its editor."""
        self._mark_modal_done()
        self.mark_modal_finishing()
        focused = False
        try:
            self.__exit_modal__()
            from ..utils.selection import focus_element_settings
            focused = focus_element_settings(element)
            from ..gesture.gesture_input import clear_gesture_item_memos
            clear_gesture_item_memos(self.session, self)
        finally:
            self.clear_modal_finishing()
            from ..utils.ui_draw_sync import (
                cancel_modal_ui_refresh,
                tag_gesture_ui_regions,
            )
            cancel_modal_ui_refresh()
            tag_gesture_ui_regions()

        if not focused:
            return {'FINISHED'}
        try:
            result = bpy.ops.wm.gesture_show_preferences('EXEC_DEFAULT')
        except (AttributeError, RuntimeError, TypeError):
            return {'FINISHED'}
        if 'FINISHED' in result:
            return {'FINISHED', 'INTERFACE'}
        return {'FINISHED'}

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
        # Blender may call cancel after our modal branch already cleaned up.
        if (
                getattr(self, "_modal_cleaned", False)
                and not getattr(self, "_modal_cancelled", False)
        ):
            return
        self._cancel_modal()

    def __exit_modal__(self):
        if getattr(self, "_modal_cleaned", False):
            return
        operator_setattr(self, "_modal_cleaned", True)
        try:
            self.unregister_draw()
        finally:
            try:
                # A cancelled/deactivated modal has no final-dispatch wrapper
                # to do this. Avoid leaving the post-modal poller around to tag
                # the same UI regions again after the handler was removed.
                if id(self) not in GestureGpuDraw.__finishing_draw_instances__:
                    from ..utils.ui_draw_sync import cancel_modal_ui_refresh
                    cancel_modal_ui_refresh()
            finally:
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
