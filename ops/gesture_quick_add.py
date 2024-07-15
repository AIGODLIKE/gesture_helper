import bpy
from mathutils import Vector

from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..lib.bpu import BpuLayout
from ..utils.public import PublicOperator, PublicProperty


class GestureQuickAddDraw(GestureGpuDraw, PublicProperty):
    __draw_class__ = {}

    def __init__(self):
        self.start_mouse_position = None
        self.mouse_position = Vector((0, 0))

    @property
    def is_exit(self):
        return self.is_right_mouse


class GestureQuickAdd(GestureQuickAddDraw, PublicOperator):
    bl_idname = "gesture.quick_add"
    bl_label = "Quick Add"

    def __init__(self):
        self.__difference_mouse__ = None
        self.bpu = BpuLayout()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.mouse_position = self.start_mouse_position
        self.init_invoke(event)

        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print(event.type, event.value, "\tprev", event.type_prev, event.value_prev)
        self.init_module(event)
        self.bpu.register_draw()

        nm = Vector((event.mouse_x, event.mouse_y))
        if event.type == "SPACE" or (event.type == "MOUSEMOVE" and event.type_prev == "SPACE"):
            if event.value == "PRESS":
                self.__difference_mouse__ = self.start_mouse_position - nm
            elif event.value == "RELEASE":
                self.__difference_mouse__ = None
            elif self.__difference_mouse__:
                nd = self.start_mouse_position - nm
                d = self.__difference_mouse__ - nd
                self.mouse_position = nm - d
            return {'PASS_THROUGH', 'RUNNING_MODAL'}

        if self.is_exit:
            self.unregister_draw()
            self.bpu.unregister_draw()
            return {'FINISHED'}
        return {'PASS_THROUGH'}
