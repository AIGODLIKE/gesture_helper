# Display operator,
# toggle

import bpy
from bpy.app.translations import pgettext_iface
from bpy.props import StringProperty

from ..gesture import GestureProperty
from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..gesture.gesture_handle import GestureHandle
from ..gesture.gesture_pass_through_keymap import GesturePassThroughKeymap
from ..utils.public import PublicOperator, debug_print


class GestureOperator(PublicOperator, GestureHandle, GestureGpuDraw, GestureProperty, GesturePassThroughKeymap, ):
    bl_idname = 'wm.gesture_operator'
    bl_label = 'Gesture Operator'
    gesture: StringProperty()
    extension_hover = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extension_hover = []
        self.screen = None
        self.area = None
        self.timer = None

    def draw_error(self, __):
        layout = self.layout
        for text in [
            "No gesture found to draw",
            "Possible errors in keymap",
            "Please go to the plugin preference settings to restore keymap",
        ]:
            layout.label(text=text)

    def invoke(self, context, event):
        if pass_d := self.try_pass_annotations_eraser(context, event):
            return pass_d
        if pass_right_mouse := self.try_pass_paint_texture_stencil(context, event):
            return pass_right_mouse

        if self.operator_gesture is None:
            context.window_manager.popup_menu(self.__class__.draw_error,
                                              title=pgettext_iface("Error"),
                                              icon="INFO")
            return {'CANCELLED'}

        self.register_draw()
        self.init_trajectory()
        self.init_invoke(event)
        self.cache_clear()

        debug_print(
            "invoke", self.bl_idname,
            f"\tmodal\t{event.value}\t{event.type}",
            "\tprev", event.type_prev, event.value_prev,
            key='modal',
        )

        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 24, window=context.window)
        wm.modal_handler_add(self)
        debug_print(self.bl_idname, event.type, event.value, key='modal')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.trajectory_event_update(context, event)
        self.init_modal(event)
        debug_print(self.bl_idname, f"\tmodal\t{event.value}\t{event.type}", "\tprev", event.type_prev, event.value_prev, key='modal')
        if self.try_immediate_implementation():
            self.__exit_modal__()
            return {"FINISHED"}
        if self.is_exit:
            self.__exit_modal__()
            return self.exit(context, event)
        return {'RUNNING_MODAL'}

    def exit(self, context: bpy.types.Context, event: bpy.types.Event):
        ops = self.try_running_operator(self)

        if self.is_debug:
            debug_print('ops', ops, key='modal')
            debug_print(
                self.is_draw_gesture, self.is_beyond_threshold_confirm,
                self.is_draw_gpu, self.is_beyond_threshold,
                key='modal',
            )

        if not ops:
            if not self.is_draw_gesture and not self.is_beyond_threshold_confirm:
                if self.is_debug:
                    area = context.area
                    view_type = getattr(context.space_data, "view_type", None)
                    view = getattr(context.space_data, "view", None)
                    mode = getattr(context.space_data, "mode", None)

                    region_type = bpy.context.region.type
                    debug_print(
                        f'PASS_THROUGH EVENT\tTYPE:{self.event.type}\t\tVALUE:{self.event.value}',
                        key='modal',
                    )
                    debug_print(
                        f"Context Mode:{context.mode}\tAREA:{area.type}\tREGION:{region_type}",
                        key='modal',
                    )
                    debug_print(
                        f"SPACE_DATA\tview_type:{view_type}\tview:{view}\tmode:{mode}",
                        key='modal',
                    )
                self.try_pass_through_keymap(context, event)
                return {'FINISHED', 'PASS_THROUGH', 'INTERFACE'}
        return {'FINISHED'}

    def cancel(self, context):
        self.__exit_modal__()

    def __exit_modal__(self):
        self.unregister_draw()
        if self.timer is not None:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def try_immediate_implementation(self):
        """Try to run operator immediately."""
        if self.gesture_property.immediate_implementation:
            de = self.direction_element
            if de and self.is_beyond_threshold_confirm and self.is_draw_gesture:
                if de.is_operator:
                    res = self.try_running_operator(self)
                    return True

    @property
    def mouse_is_in_extension_any_area(self) -> bool:
        if self.extension_element and len(self.extension_hover):
            for (index, last) in enumerate(self.extension_hover):
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
