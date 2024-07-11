# 显示操作符,
# 切换

import bpy
from bpy.props import StringProperty

from ..gesture import GestureProperty
from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..gesture.gesture_handle import GestureHandle
from ..gesture.gesture_pass_through_keymap import GesturePassThroughKeymap
from ..utils.public import PublicOperator


class GestureOperator(GestureHandle, GestureGpuDraw, GestureProperty, GesturePassThroughKeymap, PublicOperator):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Operator'

    gesture: StringProperty()

    timer = None

    def invoke(self, context, event):
        self.init_invoke(event)
        self.cache_clear()
        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 5, window=context.window)
        wm.modal_handler_add(self)
        if self.is_debug:
            print(self.bl_idname, event.type, event.value)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self.is_debug:
            print(self.bl_idname, "\tmodal\t", event.type, event.value)
        self.update_modal(context, event)
        if self.is_exit:
            return self.exit(context, event)
        return {'RUNNING_MODAL'}

    def exit(self, context: bpy.types.Context, event: bpy.types.Event):
        self.unregister_draw()
        ops = self.try_running_operator()
        wm = bpy.context.window_manager
        wm.event_timer_remove(self.timer)

        if self.is_debug:
            print('ops', ops, )
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
                return {'FINISHED', 'PASS_THROUGH', 'INTERFACE'}
        else:
            ...
        return {'FINISHED'}
