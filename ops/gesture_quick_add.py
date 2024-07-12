import bpy
import gpu
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector

from ..gesture.gesture_draw_gpu import GestureGpuDraw
from ..utils.public import PublicOperator, get_debug, PublicProperty


class GestureQuickAddDraw(GestureGpuDraw, PublicProperty):
    __draw_class__ = {}

    def __init__(self):
        self.start_mouse_position = None
        self.mouse_position = Vector((0, 0))

    def gpu_draw(self):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        area = bpy.context.region
        self.draw_tips()
        with gpu.matrix.push_pop():
            gpu.matrix.translate((-area.x, -area.y))
            gpu.matrix.translate(self.mouse_position)
            draw_circle_2d([0, 0], [1, 0.5, 0.5, 0], 100.0)
            self.draw_text([0, 0], size=64)
            self.draw_text([0, 0], text=str(bpy.context.area.type), size=24)

    def draw_tips(self):
        self.draw_rectangle(0, 0, 300, 100, color=[0.800424, 0.085840, 0.174684, 1.000000])
        self.draw_text([0, 0], text="编辑手势中 按右键退出", column=-2, color=(1, 1, 1, 1), size=24)

    def register_draw(self):
        if not GestureQuickAddDraw.__draw_class__:
            if self.is_debug:
                print('register_draw')
            for cls in self.space_subclasses():
                sub_class = {}
                # bpy.types.Region.bl_rna.properties['type'].enum_items_static
                for identifier in {'WINDOW', }:  # 'UI', 'TOOLS'
                    try:
                        sub_class[identifier] = cls.draw_handler_add(self.gpu_draw, (), identifier, 'POST_PIXEL')
                    except Exception as e:
                        if self.is_debug:
                            print(e.args)
                GestureQuickAddDraw.__draw_class__[cls] = sub_class
            self.tag_redraw()

    @classmethod
    def unregister_draw(cls):
        if get_debug():
            print('unregister_draw')
        for c, debug_class in GestureQuickAddDraw.__draw_class__.items():
            for key, value in debug_class.items():
                c.draw_handler_remove(value, key)
        GestureQuickAddDraw.__draw_class__.clear()
        cls.tag_redraw()

    @property
    def is_exit(self):
        return self.is_right_mouse


class GestureQuickAdd(GestureQuickAddDraw, PublicOperator):
    bl_idname = "gesture.quick_add"
    bl_label = "Quick Add"

    def __init__(self):
        self.__difference_mouse__ = None

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        self.start_mouse_position = Vector((event.mouse_x, event.mouse_y))
        self.mouse_position = self.start_mouse_position
        self.init_invoke(event)

        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print(event.type, event.value, "\tprev", event.type_prev, event.value_prev)
        self.register_draw()
        self.init_module(event)

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
            return {'FINISHED'}
        return {'PASS_THROUGH'}
