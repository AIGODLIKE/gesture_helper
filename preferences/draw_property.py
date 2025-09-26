import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, FloatVectorProperty, StringProperty, IntVectorProperty

from ..utils.public import get_pref


class DrawProperty(bpy.types.PropertyGroup):
    from ..utils import public_color
    gesture_show_enabled_button: BoolProperty(name='Show enable/disable button', default=True)
    gesture_show_keymap: BoolProperty(name='Show keymap', default=True)
    gesture_show_description: BoolProperty(name='Show description', default=True)
    gesture_keymap_split_factor: FloatProperty(name='Keymap split factor', default=0.2, max=0.95, min=0.01, step=0.01)
    gesture_remove_tips: BoolProperty(name='Gesture remove tips', default=True,
                                      description="If you turn on \n, a pop-up will appear when you delete it.")
    gesture_point_name_size: IntProperty(name='Gesture Point Name Size', description='Gpu Draw Point Name Size',
                                         default=15, min=5,
                                         max=60)

    element_split_factor: FloatProperty(name='Split Factor', default=0.2, max=0.95, min=0.01, step=0.01)
    element_show_enabled_button: BoolProperty(name='Show enable/disable button', default=True)
    element_show_left_side: BoolProperty(name='Show in left side', default=False)
    element_show_icon: BoolProperty(name='Show icon', default=True)
    element_remove_tips: BoolProperty(name='Element remove tips', default=True,
                                      description="If you turn on \n, a pop-up will appear when you delete it.")
    element_extension_item_offset: FloatProperty(name='Extension Offset', default=4, max=10, min=3, step=.5)

    element_draw_child_icon: BoolProperty(name="Child Icon",description="Draw Child Icon", default=True)
    element_draw_property_toggle_icon: BoolProperty(
        name='Property Icon',
        description="Draw Toggle property operator icon",
        default=True)

    text_gpu_draw_size: IntProperty(name='Text', description='Gpu Draw Text Size', default=18, min=5, max=120)
    text_gpu_draw_radius: IntProperty(name='Rounded corner size', description='Gpu Draw Radius Size', default=5, min=2,
                                      max=60)
    text_gpu_draw_margin: IntVectorProperty(name='Margin', description='Gpu Draw Margin Size',
                                            default=(12, 10),
                                            min=0,
                                            max=120,
                                            size=2)
    line_width: IntProperty(name='Line Width', description='Gpu Draw Width Size', default=3, min=1, max=20)
    dividing_line_height: IntProperty(name='Dividing Line Height', description='Gpu Draw Dividing Line Height',
                                      default=3, min=1, max=10)

    background_operator_color: FloatVectorProperty(name='Operator Color', **public_color,
                                                   default=[0.009134, 0.009134, 0.009134, 1.000000])
    background_operator_active_color: FloatVectorProperty(name='Operator Active Color', **public_color,
                                                          default=[0.063012, 0.168268, 0.450780, 1.000000])
    background_child_color: FloatVectorProperty(name='Child Color', **public_color,
                                                default=[0.009134, 0.009134, 0.009134, 1.000000])
    background_child_active_color: FloatVectorProperty(name='Child Active Color', **public_color,
                                                       default=[0.063012, 0.168268, 0.450780, 1.000000])
    background_bool_true: FloatVectorProperty(name='Bool True Color', **public_color,
                                              default=[0.063012, 0.168268, 0.450780, 1.000000])
    background_bool_false: FloatVectorProperty(name='Bool False Color', **public_color,
                                               default=[0.009134, 0.009134, 0.009134, 1.000000])

    text_default_color: FloatVectorProperty(name='Text Default Color', **public_color, default=(.8, .8, .8, 1))
    text_active_color: FloatVectorProperty(name='Text Active Color', **public_color, default=(1, 1, 1, 1))

    trajectory_mouse_color: FloatVectorProperty(name='Mouse Track Color', **public_color,
                                                default=[0.100000, 0.900000, 1.000000, 1.000000])
    trajectory_gesture_color: FloatVectorProperty(name='Gesture Track Color', **public_color,
                                                  default=[0.689335, 0.275156, 0.793810, 1.000000])

    dividing_line_color: FloatVectorProperty(name='Dividing Line Color', **public_color,
                                             default=[0.143718, 0.143718, 0.143718, 1.000000])

    def __update_panel_name__(self, context):
        from ..ui.panel import update_panel
        update_panel()

    panel_enable: BoolProperty(name='Enabled Panel', default=True, update=__update_panel_name__)
    panel_name: StringProperty(name='Panel Name', default='Gesture', update=__update_panel_name__)
    author: StringProperty(name='Author', default='小萌新')
    enable_name_translation: BoolProperty(name='Name Translation', default=True)

    @staticmethod
    def draw_text_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        draw = pref.draw_property

        radius_is_alert = draw.text_gpu_draw_radius > min(draw.text_gpu_draw_margin)

        col = layout.box().column(align=True)
        col.prop(draw, 'element_draw_child_icon')
        col.prop(draw, 'element_draw_property_toggle_icon')
        col.prop(draw, 'text_gpu_draw_size')
        cr = col.row(align=True)
        cr.alert = radius_is_alert
        cr.prop(draw, 'text_gpu_draw_radius')
        col.separator()
        col.prop(draw, 'element_extension_item_offset')
        col.separator()
        col.prop(draw, 'text_gpu_draw_margin')
        col.separator()
        col.prop(draw, 'gesture_point_name_size')
        col.prop(draw, 'line_width')
        if radius_is_alert:
            cb = col.box()
            cb.alert = True
            cb.label(text="Error, rounded corners are larger than the margins")
            cb.label(text="The size of the rounded corners is clamped by the margins")
        col.separator()
        col.prop(draw, 'dividing_line_height')

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
        bb.prop(draw, 'background_bool_false')
        bb.prop(draw, 'background_bool_true')

        bb = box.column(align=True)
        bb.prop(draw, 'text_default_color')
        bb.prop(draw, 'text_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'trajectory_mouse_color')
        bb.prop(draw, 'trajectory_gesture_color')

        bb = box.column(align=True)
        bb.prop(draw, 'dividing_line_color')
