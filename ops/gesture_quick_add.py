import bpy
from mathutils import Vector

from ..lib.bpu import BpuLayout
from ..utils.public import PublicOperator


class GestureQuickAddKeymap:
    """注册快捷键"""
    kc = bpy.context.window_manager.keyconfigs.addon  # 获取按键配置addon的
    km = kc.keymaps.new(name='Window', space_type='EMPTY', region_type='WINDOW')
    kmi = None

    @classmethod
    def register(cls):
        cls.kmi = cls.km.keymap_items.new(GestureQuickAdd.bl_idname, 'ACCENT_GRAVE', 'PRESS',
                                          ctrl=True, alt=True, shift=True)

    @classmethod
    def unregister(cls):
        cls.km.keymap_items.remove(cls.kmi)


class GestureQuickAdd(PublicOperator):
    bl_idname = "gesture.quick_add"
    bl_label = "Quick Add"
    is_in_quick_add = False  # 是在添加模式

    def __init__(self):
        super().__init__()
        self.__difference_mouse__ = None
        self.bpu = BpuLayout()

        self.start_mouse_position = None
        self.mouse_position = Vector((0, 0))

    @classmethod
    def poll(cls, context):
        return not cls.is_in_quick_add

    @property
    def is_exit(self):
        return self.is_right_mouse

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.mouse_position = self.start_mouse_position
        self.init_invoke(event)

        wm = context.window_manager
        wm.modal_handler_add(self)
        GestureQuickAdd.is_in_quick_add = True

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print(event.type, event.value, "\tprev", event.type_prev, event.value_prev)
        self.init_module(event)
        self.bpu.register_draw()

        nm = Vector((event.mouse_x, event.mouse_y))

        with self.bpu as bpu:
            bpu.mouse_position = self.mouse_position
            column = bpu.column()
            for i in range(4):
                column.label(f"text {i}")
            column.label(event.type)
            column.label(event.value)

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
            self.bpu.unregister_draw()
            GestureQuickAdd.is_in_quick_add = False
            return {'FINISHED'}
        return {'PASS_THROUGH'}
