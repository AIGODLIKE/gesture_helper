import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, FloatVectorProperty
from bpy.types import PropertyGroup

from ..utils.public import get_pref


class DrawProperty(PropertyGroup):
    from ..utils import public_color
    element_split_factor: FloatProperty(name='拆分系数', default=0.09, max=0.95, min=0.01)
    element_show_enabled_button: BoolProperty(name='显示 启用/禁用 按钮', default=True)
    element_show_left_side: BoolProperty(name='显示在左侧', default=False)

    text_gpu_draw_size: IntProperty(name='文字大小', description='Gpu绘制的文字大小', default=20, min=5, max=120)
    text_gpu_draw_radius: IntProperty(name='圆角大小', description='Gpu绘制的圆角大小', default=10, min=5, max=120)
    text_gpu_draw_margin: IntProperty(name='Margin', description='Gpu绘制的Margin大小', default=7, min=5, max=120)
    line_width: IntProperty(name='线宽', description='Gpu绘制的线宽大小', default=5, min=2, max=20)

    background_operator_color: FloatVectorProperty(name='操作符颜色', **public_color,
                                                   default=[0.019382, 0.019382, 0.019382, 1.000000])
    background_child_color: FloatVectorProperty(name='子级颜色', **public_color,
                                                default=[0.431968, 0.222035, 0.650622, 1.000000])
    background_active_color: FloatVectorProperty(name='活动颜色', **public_color,
                                                 default=[0.738785, 0.776229, 1.000000, 1.000000])

    text_default_color: FloatVectorProperty(name='文字默认颜色', **public_color, default=(.8, .8, .8, 1))
    text_active_color: FloatVectorProperty(name='文字活动颜色', **public_color, default=(1, 1, 1, 1))
    mouse_trajectory_color: FloatVectorProperty(name='鼠标轨迹颜色', **public_color, default=(.1, .9, 1, 1))
    gesture_trajectory_color: FloatVectorProperty(name='手势轨迹颜色', **public_color, default=(0, .7, .9, 1))

    @staticmethod
    def draw_text_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        draw = pref.draw_property

        col = layout.box()
        col.prop(draw, 'text_gpu_draw_size')
        col.prop(draw, 'text_gpu_draw_radius')
        col.prop(draw, 'text_gpu_draw_margin')
        col.prop(draw, 'line_width')

    @staticmethod
    def draw_color_property(layout: bpy.types.UILayout):
        pref = get_pref()
        draw = pref.draw_property
        box = layout.box()
        box.label(text="Color")

        bb = box.column(heading="背景")
        bb.prop(draw, 'background_operator_color')
        bb.prop(draw, 'background_child_color')
        bb.prop(draw, 'background_active_color')

        bb = box.column(heading="字体")
        bb.prop(draw, 'text_default_color')
        bb.prop(draw, 'text_active_color')

        bb = box.column(heading="轨迹")
        bb.prop(draw, 'mouse_trajectory_color')
        bb.prop(draw, 'gesture_trajectory_color')

