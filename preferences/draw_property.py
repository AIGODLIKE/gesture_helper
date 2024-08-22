import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, FloatVectorProperty, StringProperty
from bpy.types import PropertyGroup

from ..utils.public import get_pref


class DrawProperty(PropertyGroup):
    from ..utils import public_color
    gesture_show_enabled_button: BoolProperty(name='Show enable/disable button', default=True)
    gesture_show_keymap: BoolProperty(name='Show keymap', default=True)
    gesture_show_description: BoolProperty(name='Show description', default=True)
    gesture_keymap_split_factor: FloatProperty(name='Keymap split factor', default=0.2, max=0.95, min=0.01, step=0.01)
    gesture_remove_tips: BoolProperty(name='Gesture remove tips', default=True, description="If you turn on \n, a pop-up will appear when you delete it.")

    element_split_factor: FloatProperty(name='Split Factor', default=0.2, max=0.95, min=0.01)
    element_show_enabled_button: BoolProperty(name='Show enable/disable button', default=True)
    element_show_left_side: BoolProperty(name='Show in left side', default=False)
    element_remove_tips: BoolProperty(name='Element remove tips', default=True, description="If you turn on \n, a pop-up will appear when you delete it.")

    text_gpu_draw_size: IntProperty(name='Font Size', description='Gpu Draw Text Size', default=20, min=5, max=120)
    text_gpu_draw_radius: IntProperty(name='Radius Size', description='Gpu Draw Radius Size', default=7, min=5, max=120)
    text_gpu_draw_margin: IntProperty(name='Margin', description='Gpu Draw Margin Size', default=20, min=5, max=120)
    line_width: IntProperty(name='Line Width', description='Gpu Draw Width Size', default=3, min=1, max=20)

    background_operator_color: FloatVectorProperty(name='Operator Color', **public_color,
                                                   default=[0.019382, 0.019382, 0.019382, 1.000000])
    background_operator_active_color: FloatVectorProperty(name='Operator Active Color', **public_color,
                                                          default=[0.331309, 0.347597, 0.445060, 1.000000])

    background_child_color: FloatVectorProperty(name='Child Color', **public_color,
                                                default=[0.431968, 0.222035, 0.650622, 1.000000])
    background_child_active_color: FloatVectorProperty(name='Child Active Color', **public_color,
                                                       default=[0.689335, 0.275156, 0.793810, 1.000000])

    text_default_color: FloatVectorProperty(name='Text Default Color', **public_color, default=(.8, .8, .8, 1))
    text_active_color: FloatVectorProperty(name='Text Active Color', **public_color, default=(1, 1, 1, 1))

    trajectory_mouse_color: FloatVectorProperty(name='Mouse Track Color', **public_color,
                                                default=[0.100000, 0.900000, 1.000000, 1.000000])
    trajectory_gesture_color: FloatVectorProperty(name='Gesture Track Color', **public_color,
                                                  default=[0.689335, 0.275156, 0.793810, 1.000000])
    
    def __update_panel_name__(self, context):
        from ..ui.panel import update_panel
        update_panel()

    panel_name: StringProperty(name='Panel Name', default='Gesture', update=__update_panel_name__)

    @staticmethod
    def draw_text_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        draw = pref.draw_property

        col = layout.box().column(align=True)
        col.prop(draw, 'text_gpu_draw_size')
        col.prop(draw, 'text_gpu_draw_radius')
        col.prop(draw, 'text_gpu_draw_margin')
        col.prop(draw, 'line_width')

    @staticmethod
    def draw_color_property(layout: bpy.types.UILayout):
        pref = get_pref()
        draw = pref.draw_property
        box = layout.box()

        bb = box.column(align=True)
        bb.prop(draw, 'background_operator_color')
        bb.prop(draw, 'background_operator_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'background_child_color')
        bb.prop(draw, 'background_child_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'text_default_color')
        bb.prop(draw, 'text_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'trajectory_mouse_color')
        bb.prop(draw, 'trajectory_gesture_color')
