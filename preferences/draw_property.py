import bpy
from bpy.props import FloatProperty, BoolProperty, IntProperty, FloatVectorProperty, StringProperty, IntVectorProperty

from ..utils import theme_defaults
from ..utils.public import get_pref


class DrawProperty(bpy.types.PropertyGroup):
    from ..utils import public_color
    gesture_show_enabled_button: BoolProperty(
        name='Show enable/disable button',
        description='Show the enable/disable toggle for each gesture in the list',
        default=True,
    )
    gesture_show_keymap: BoolProperty(
        name='Show keymap',
        description='Show keymap text next to each gesture in the list',
        default=True,
    )
    gesture_show_description: BoolProperty(
        name='Show description',
        description='Show the gesture description in the list',
        default=True,
    )
    gesture_keymap_split_factor: FloatProperty(
        name='Keymap split factor',
        description='List column width ratio used when showing gesture keymaps',
        default=0.2, max=0.95, min=0.01, step=0.01,
    )
    gesture_remove_tips: BoolProperty(
        name='Confirm gesture delete',
        default=True,
        description='Ask for confirmation before deleting a gesture',
    )
    gesture_point_name_size: IntProperty(
        name='Direction label size',
        description='Font size for direction labels on the gesture ring',
        default=15, min=5, max=60,
    )

    element_split_factor: FloatProperty(
        name='Split Factor',
        description='Width ratio between the element list and the property panel',
        default=0.2, max=0.95, min=0.01, step=0.01,
    )
    element_show_enabled_button: BoolProperty(
        name='Show enable/disable button',
        description='Show the enable/disable toggle for each element in the list',
        default=True,
    )
    element_show_left_side: BoolProperty(
        name='Show on the left',
        description='Show the element property panel on the left side of the layout',
        default=False,
    )
    element_show_icon: BoolProperty(
        name='Show icon',
        description='Show icons for elements in the list',
        default=True,
    )
    element_remove_tips: BoolProperty(
        name='Confirm element delete',
        default=True,
        description='Ask for confirmation before deleting an element',
    )
    element_extension_item_offset: FloatProperty(
        name='Extension Offset',
        description='Spacing offset for extension menu items when drawing gestures',
        default=4, max=10, min=3, step=.5,
    )

    element_draw_child_icon: BoolProperty(
        name='Child icon',
        description='Show an icon on elements that have child items',
        default=True,
    )
    element_draw_property_toggle_icon: BoolProperty(
        name='Property icon',
        description='Show an icon on property toggle elements',
        default=True,
    )

    text_gpu_draw_size: IntProperty(
        name='Text',
        description='Font size for GPU-drawn gesture text',
        default=14, min=5, max=120,
    )
    text_gpu_draw_radius: IntProperty(
        name='Corner radius',
        description='Rounded corner radius for GPU-drawn gesture buttons',
        default=6, min=2, max=60,
    )
    margin: IntVectorProperty(
        name='Margin',
        description='Inner padding for GPU-drawn gesture buttons',
        default=(10, 6),
        min=0,
        max=120,
        size=2,
    )
    line_width: IntProperty(
        name='Line Width',
        description='Stroke width for GPU-drawn gesture outlines',
        default=2, min=1, max=20,
    )
    outline_width: FloatProperty(
        name='Outline Width',
        description='Stroke width for flat outlined gesture buttons',
        default=theme_defaults.OUTLINE_WIDTH, min=0.25, max=4.0, step=5, precision=2,
    )
    dividing_line_height: IntProperty(
        name='Divider height',
        description='Height of divider lines between gesture UI sections',
        default=2, min=1, max=10,
    )

    # Scene-linear defaults (shared with BPU via theme_defaults); GPU draw converts to sRGB.
    background_operator_color: FloatVectorProperty(name='Operator Color', **public_color,
                                                   default=theme_defaults.BACKGROUND)
    background_operator_active_color: FloatVectorProperty(name='Operator Active Color', **public_color,
                                                          default=theme_defaults.OPERATOR_ACTIVE)
    background_child_color: FloatVectorProperty(name='Child Color', **public_color,
                                                default=theme_defaults.BACKGROUND)
    background_child_active_color: FloatVectorProperty(name='Child Active Color', **public_color,
                                                       default=theme_defaults.CHILD_ACTIVE)
    background_bool_true: FloatVectorProperty(name='Bool True Color', **public_color,
                                              default=theme_defaults.OPERATOR_ACTIVE)
    background_bool_false: FloatVectorProperty(name='Bool False Color', **public_color,
                                               default=theme_defaults.BACKGROUND)

    text_default_color: FloatVectorProperty(name='Text Default Color', **public_color,
                                            default=theme_defaults.TEXT_DEFAULT)
    text_active_color: FloatVectorProperty(name='Text Active Color', **public_color,
                                           default=theme_defaults.TEXT_ACTIVE)

    trajectory_mouse_color: FloatVectorProperty(name='Mouse Track Color', **public_color,
                                                default=theme_defaults.TRAJECTORY_MOUSE)
    trajectory_gesture_color: FloatVectorProperty(name='Gesture Track Color', **public_color,
                                                  default=theme_defaults.TRAJECTORY_GESTURE)

    dividing_line_color: FloatVectorProperty(name='Dividing Line Color', **public_color,
                                             default=theme_defaults.DIVIDING_LINE)
    outline_color: FloatVectorProperty(name='Outline Color', **public_color,
                                       default=theme_defaults.OUTLINE)
    outline_active_color: FloatVectorProperty(name='Outline Active Color', **public_color,
                                              default=theme_defaults.OUTLINE_ACTIVE)

    def __update_panel_name__(self, context):
        from ..ui.panel import update_panel
        update_panel()

    panel_enable: BoolProperty(
        name='Enable Panel',
        description='Show the Gesture Helper panel in the N-panel sidebar',
        default=True,
        update=__update_panel_name__,
    )
    panel_name: StringProperty(
        name='Panel Name',
        description='Category name of the N-panel tab',
        default='Gesture',
        update=__update_panel_name__,
    )
    author: StringProperty(
        name='Author',
        description='Author name written into exported gesture presets',
        default='小萌新',
    )
    enable_name_translation: BoolProperty(
        name='Name Translation',
        description='Translate gesture and element display names when the Blender UI language is not English',
        default=True,
    )

    @staticmethod
    def draw_text_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        draw = pref.draw_property

        radius_is_alert = draw.text_gpu_draw_radius > min(draw.margin)

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
        col.prop(draw, 'margin')
        col.separator()
        col.prop(draw, 'gesture_point_name_size')
        col.prop(draw, 'line_width')
        col.prop(draw, 'outline_width')
        if radius_is_alert:
            cb = col.box()
            cb.alert = True
            cb.label(text="Corner radius is larger than the margin")
            cb.label(text="Corners are clamped to the smaller margin")
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
        bb.prop(draw, 'outline_color')
        bb.prop(draw, 'outline_active_color')
