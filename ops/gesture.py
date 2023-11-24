# 显示操作符,
# 切换
import bpy
from bpy.props import StringProperty

from ..utils.public import PublicOperator
from ..utils.public_gpu import PublicGpu


class GestureGpuDraw(PublicGpu, PublicOperator):
    __temp_draw_class__ = {}

    @property
    def region_enum_type(self):
        return bpy.types.Region.bl_rna.properties['type'].enum_items_static

    @property
    def is_window_region_type(self):
        return bpy.context.region.type == 'WINDOW'

    @property
    def mouse_x(self):
        region = bpy.context.region
        return self.event.mouse_x - region.x

    @property
    def mouse_y(self):
        region = bpy.context.region
        return self.event.mouse_y - region.y

    @staticmethod
    def refresh_space():
        return list(getattr(bpy.types, i) for i in dir(bpy.types) if 'Space' in i)

    @classmethod
    def space_subclasses(cls):
        cls.refresh_space()
        return bpy.types.Space.__subclasses__()

    def register_draw(self):
        print('register_draw')
        for cls in self.space_subclasses():
            sub_class = {}
            for j in self.region_enum_type:
                identifier = j.identifier
                try:
                    sub_class[identifier] = cls.draw_handler_add(self.gpu_draw, (), identifier, 'POST_PIXEL')
                except Exception as e:
                    ...
            GestureGpuDraw.__temp_draw_class__[cls] = sub_class
        self.tag_redraw()

    @classmethod
    def unregister_draw(cls):
        print('unregister_draw')
        for c, sub_class in GestureGpuDraw.__temp_draw_class__.items():
            for key, value in sub_class.items():
                c.draw_handler_remove(value, key)
        GestureGpuDraw.__temp_draw_class__.clear()
        cls.tag_redraw()

    def gpu_draw_debug(self):
        self.draw_rectangle(0, 0, 400, 700)
        area = bpy.context.area
        region = bpy.context.region
        for index, i in enumerate((
                'area.x:' + str(area.x),
                'area.y:' + str(area.y),
                'area.height:' + str(area.height),
                'area.width:' + str(area.width),
                'area.type:' + str(area.type),
                '--',
                'region.x:' + str(region.x),
                'region.y:' + str(region.y),
                'region.height:' + str(region.height),
                'region.width:' + str(region.width),
                'region.type:' + str(region.type),
                '--',
                'x:' + str(self.event.mouse_x),
                'y:' + str(self.event.mouse_y),
                'mouse_prev_press_x:' + str(self.event.mouse_prev_press_x),
                'mouse_prev_press_y:' + str(self.event.mouse_prev_press_y),
                'mouse_region_x:' + str(self.event.mouse_region_x),
                'mouse_region_y:' + str(self.event.mouse_region_y),
                'mouse_prev_x:' + str(self.event.mouse_prev_x),
                'mouse_prev_y:' + str(self.event.mouse_prev_y),
                'mouse_x:' + str(self.event.mouse_x),
                'mouse_y:' + str(self.event.mouse_y),
        )):
            j = index + 1
            self.draw_text(0, 30 * j, text=i)

    def gpu_draw(self):
        if self.is_window_region_type:
            self.gpu_draw_debug()
        event = self.event
        self.draw_text(self.mouse_x, self.mouse_y, text=event.value)
        self.draw_rounded_rectangle((self.mouse_x, self.mouse_y), (1, 1, 1, 1), radius=120, segments=128)


class GestureOperator(GestureGpuDraw):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Opeator'

    gesture: StringProperty()

    def invoke(self, context, event):
        self.init_invoke(event)
        self.register_draw()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.init_module(event)
        self.tag_redraw()
        print('modal', context, event.value, event.type)
        if self.is_right_mouse and self.is_release:
            return self.exit()
        return {'RUNNING_MODAL'}

    def exit(self):
        self.unregister_draw()
        return {'FINISHED'}
