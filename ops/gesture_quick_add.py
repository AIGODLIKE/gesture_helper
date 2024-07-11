import bpy

from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..utils.public import PublicOperator


class GestureQuickAddDraw(GestureGpuDraw):
    __temp_draw_class__ = {}


class GestureQuickAdd(GestureQuickAddDraw, PublicOperator):
    bl_idname = "gesture.quick_add"
    bl_label = "Quick Add"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.init_invoke(event)
        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.init_module(event)
        if self.is_exit:
            return {'FINISHED'}
        return {'RUNNING_MODAL', 'PASS_THROUGH'}
