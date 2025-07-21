# 显示操作符,
# 切换

import bpy
from bpy.props import StringProperty
from bpy.app.translations import pgettext_iface
from ..gesture import GestureProperty
from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..gesture.gesture_handle import GestureHandle
from ..gesture.gesture_pass_through_keymap import GesturePassThroughKeymap
from ..utils.public import PublicOperator


class GestureOperator(PublicOperator, GestureHandle, GestureGpuDraw, GestureProperty, GesturePassThroughKeymap, ):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Operator'
    gesture: StringProperty()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.screen = None
        self.area = None

    def draw_error(self, __):
        layout = self.layout
        for text in [
            "No gesture found to draw",
            "Possible errors in keymap",
            "Please go to the plugin preference settings to restore keymap",
        ]:
            layout.label(text=text)

    def invoke(self, context, event):
        self.register_draw()
        self.init_trajectory()
        self.init_invoke(event)
        self.cache_clear()

        print("invoke", self.bl_idname, f"\tmodal\t{event.value}\t{event.type}", "\tprev", event.type_prev,
              event.value_prev)
        if self.operator_gesture is None:
            context.window_manager.popup_menu(self.__class__.draw_error,
                                              title=pgettext_iface("Error"),
                                              icon="INFO")
            return {'CANCELLED'}
        pass_d = self.try_pass_annotations_eraser(context, event)
        if pass_d:
            return pass_d

        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 5, window=context.window)
        wm.modal_handler_add(self)
        if self.is_debug:
            print(self.bl_idname, event.type, event.value)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.event_trajectory(context, event)
        self.init_module(event)
        if self.is_debug:
            print(self.bl_idname, f"\tmodal\t{event.value}\t{event.type}", "\tprev", event.type_prev, event.value_prev)
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
            print('ops', ops)
            print(self.is_draw_gesture, self.is_beyond_threshold_confirm, self.is_draw_gpu, self.is_beyond_threshold)
            print()

        if not ops:
            if not self.is_draw_gesture and not self.is_beyond_threshold_confirm:
                if self.is_debug:
                    area = context.area
                    view_type = getattr(context.space_data, "view_type", None)
                    view = getattr(context.space_data, "view", None)
                    mode = getattr(context.space_data, "mode", None)

                    region_type = bpy.context.region.type
                    print(f'PASS_THROUGH EVENT\tTYPE:{self.event.type}\t\tVALUE:{self.event.value}')
                    print(f"Context Mode:{context.mode}\tAREA:{area.type}\tREGION:{region_type}")
                    print(f"SPACE_DATA\tview_type:{view_type}\tview:{view}\tmode:{mode}")
                self.try_pass_through_keymap(context, event)
                print()
                return {'FINISHED', 'PASS_THROUGH', 'INTERFACE'}
        else:
            self.report({'INFO'}, self.direction_element.name_translate)
        return {'FINISHED'}

    def cancel(self, context):
        self.__exit_modal__()

    def __exit_modal__(self):
        self.unregister_draw()
        wm = bpy.context.window_manager
        wm.event_timer_remove(self.timer)

    def try_immediate_implementation(self):
        if self.gesture_property.immediate_implementation:
            de = self.direction_element
            if de and self.is_beyond_threshold_confirm and self.is_draw_gesture:
                if de.is_operator:
                    res = self.try_running_operator(self)
                    return res
