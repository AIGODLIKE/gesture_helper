import bpy
from mathutils import Vector

from .draw_gpu import DrawGpu
from ..gesture import GestureOperator


class GestureQuickAdd(GestureOperator):
    bl_idname = "gesture.quick_add"
    bl_label = "Quick Add"
    is_quick_add_mode = False  # 是在添加模式

    offset = Vector([500, 0])

    def __init__(self):
        super().__init__()
        self.mouse_position = None
        self.__difference_mouse__ = None

        self.start_mouse_position = None
        self.offset_position = Vector((0, 0))

        self.gpu = DrawGpu()

    @classmethod
    def poll(cls, context):
        return not cls.is_quick_add_mode

    @property
    def is_exit(self):
        return self.is_right_mouse

    @property
    def is_draw_gesture(self) -> bool:
        if self.draw_trajectory_mouse_move:
            return True
        return self.operator_time

    def __sync_gesture__(self):
        """同步手势名称"""
        ag = self.pref.active_gesture
        if ag:
            self.gesture = ag.name

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.init_invoke(event)

        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.offset_position = self.start_mouse_position

        self.init_trajectory()
        self.event_trajectory(context)
        self.register_draw()
        self.gpu.register_draw_fun()

        wm = context.window_manager
        wm.modal_handler_add(self)
        GestureQuickAdd.is_quick_add_mode = True

        self.__sync_gesture__()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.init_module(event)
        self.__sync_gesture__()
        # print(event.type, event.value, "\tprev", event.type_prev, event.value_prev)
        # button_pointer = getattr(context, "button_pointer", None)
        # button_prop = getattr(context, "button_prop", None)
        # button_operator = getattr(context, "button_operator", None)
        # print(self.bl_idname, button_pointer, button_prop, button_operator)

        self.event_trajectory(context)
        self.mouse_position = Vector((event.mouse_x, event.mouse_y))

        res = self.gpu.draw_run(self, event)
        if res:
            return res

        m = self.modal_event(event)
        if m:
            return m
        return {'PASS_THROUGH'}

    def cancel(self, context):
        self.__exit_modal__()

    def modal_event(self, event):
        space = (event.type == "SPACE" and not event.alt and not event.ctrl and not event.shift)
        mv = (event.type == "MOUSEMOVE" and event.type_prev == "SPACE")
        if space or mv:
            if event.value == "PRESS":
                self.__difference_mouse__ = self.start_mouse_position - self.mouse_position
            elif event.value == "RELEASE":
                self.__difference_mouse__ = None
            elif self.__difference_mouse__:
                nd = self.start_mouse_position - self.mouse_position
                d = self.__difference_mouse__ - nd
                self.offset_position = self.mouse_position - d
            return {'PASS_THROUGH', 'RUNNING_MODAL'}

        if self.is_exit:
            GestureQuickAdd.is_quick_add_mode = False
            self.__exit_modal__()
            return {'FINISHED'}

    def __exit_modal__(self):
        self.unregister_draw()
        self.gpu.unregister_draw_fun()
