import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    StringProperty,
)

from ..utils import theme_defaults
from ..utils.public import get_pref
from ..utils.ui_theme import THEME_PRESET_ITEMS


_theme_apply_depth = 0


def _redraw_theme(_context=None) -> None:
    try:
        from ..utils.public import tag_redraw

        tag_redraw()
    except (AttributeError, ImportError, ReferenceError, RuntimeError):
        pass


def _on_theme_preset_update(self, context) -> None:
    global _theme_apply_depth
    if _theme_apply_depth:
        return
    if self.theme_preset == 'CUSTOM':
        _redraw_theme(context)
        return
    from ..utils.ui_theme import apply_theme_preset

    _theme_apply_depth += 1
    try:
        apply_theme_preset(self, self.theme_preset)
    finally:
        _theme_apply_depth -= 1
    _redraw_theme(context)


def _on_theme_color_update(self, context) -> None:
    """Mark hand-edited colors custom without fighting preset assignment."""
    global _theme_apply_depth
    if _theme_apply_depth:
        return
    if self.theme_preset != 'CUSTOM':
        _theme_apply_depth += 1
        try:
            self.theme_preset = 'CUSTOM'
        finally:
            _theme_apply_depth -= 1
    _redraw_theme(context)


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
    force_show_panels_during_modal: BoolProperty(
        name='Update panels during modal operations',
        description=(
            'Keep Gesture panels live during all modal operations, including '
            'Gesture Helper sessions and animation playback'
        ),
        default=False,
        options={'SKIP_SAVE'},
        update=lambda self, context: DrawProperty._on_force_show_update(context),
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
        name='Gesture item margin',
        description='Inner padding for GPU-drawn gesture buttons',
        default=(10, 6),
        min=0,
        max=120,
        size=2,
    )
    layout_margin: IntVectorProperty(
        name='Layout margin',
        description='Padding around row, column, box, and extension layouts',
        default=(5, 3),
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

    theme_preset: EnumProperty(
        name='Overlay Theme',
        description='Coordinated colors for gesture overlays and persistent menus',
        items=THEME_PRESET_ITEMS,
        default='BLENDER_DARK',
        update=_on_theme_preset_update,
    )

    # Scene-linear defaults (shared with BPU via theme_defaults); GPU draw converts to sRGB.
    overlay_background_color: FloatVectorProperty(
        name='Panel Background', **public_color,
        default=theme_defaults.PANEL_BACKGROUND,
        update=_on_theme_color_update,
    )
    overlay_header_color: FloatVectorProperty(
        name='Header', **public_color,
        default=theme_defaults.HEADER,
        update=_on_theme_color_update,
    )
    background_operator_color: FloatVectorProperty(name='Operator Color', **public_color,
                                                   default=theme_defaults.BACKGROUND,
                                                   update=_on_theme_color_update)
    background_operator_active_color: FloatVectorProperty(name='Operator Active Color', **public_color,
                                                          default=theme_defaults.OPERATOR_ACTIVE,
                                                          update=_on_theme_color_update)
    background_child_color: FloatVectorProperty(name='Child Color', **public_color,
                                                default=theme_defaults.BACKGROUND,
                                                update=_on_theme_color_update)
    background_child_active_color: FloatVectorProperty(name='Child Active Color', **public_color,
                                                       default=theme_defaults.CHILD_ACTIVE,
                                                       update=_on_theme_color_update)
    background_bool_true: FloatVectorProperty(name='Bool True Color', **public_color,
                                              default=theme_defaults.BOOL_TRUE,
                                              update=_on_theme_color_update)
    background_bool_false: FloatVectorProperty(name='Bool False Color', **public_color,
                                               default=theme_defaults.BOOL_FALSE,
                                               update=_on_theme_color_update)
    background_int_color: FloatVectorProperty(name='Int Color', **public_color,
                                              default=theme_defaults.INT,
                                              update=_on_theme_color_update)
    background_int_active_color: FloatVectorProperty(name='Int Active Color', **public_color,
                                                     default=theme_defaults.INT_ACTIVE,
                                                     update=_on_theme_color_update)
    background_float_color: FloatVectorProperty(name='Float Color', **public_color,
                                                default=theme_defaults.FLOAT,
                                                update=_on_theme_color_update)
    background_float_active_color: FloatVectorProperty(name='Float Active Color', **public_color,
                                                       default=theme_defaults.FLOAT_ACTIVE,
                                                       update=_on_theme_color_update)

    interaction_hover_color: FloatVectorProperty(
        name='Hover', **public_color,
        default=theme_defaults.HOVER,
        update=_on_theme_color_update,
    )
    interaction_pressed_color: FloatVectorProperty(
        name='Pressed', **public_color,
        default=theme_defaults.PRESSED,
        update=_on_theme_color_update,
    )

    text_default_color: FloatVectorProperty(name='Text Default Color', **public_color,
                                            default=theme_defaults.TEXT_DEFAULT,
                                            update=_on_theme_color_update)
    text_active_color: FloatVectorProperty(name='Text Active Color', **public_color,
                                           default=theme_defaults.TEXT_ACTIVE,
                                           update=_on_theme_color_update)
    text_disabled_color: FloatVectorProperty(
        name='Text Disabled Color', **public_color,
        default=theme_defaults.TEXT_DISABLED,
        update=_on_theme_color_update,
    )

    trajectory_mouse_color: FloatVectorProperty(name='Mouse Track Color', **public_color,
                                                default=theme_defaults.TRAJECTORY_MOUSE,
                                                update=_on_theme_color_update)
    trajectory_gesture_color: FloatVectorProperty(name='Gesture Track Color', **public_color,
                                                  default=theme_defaults.TRAJECTORY_GESTURE,
                                                  update=_on_theme_color_update)

    dividing_line_color: FloatVectorProperty(name='Dividing Line Color', **public_color,
                                             default=theme_defaults.DIVIDING_LINE,
                                             update=_on_theme_color_update)
    outline_color: FloatVectorProperty(name='Outline Color', **public_color,
                                       default=theme_defaults.OUTLINE,
                                       update=_on_theme_color_update)
    outline_active_color: FloatVectorProperty(name='Outline Active Color', **public_color,
                                              default=theme_defaults.OUTLINE_ACTIVE,
                                              update=_on_theme_color_update)
    status_disabled_color: FloatVectorProperty(name='Disabled Status', **public_color,
                                               default=theme_defaults.STATUS_DISABLED,
                                               update=_on_theme_color_update)
    status_warning_color: FloatVectorProperty(name='Unavailable Status', **public_color,
                                              default=theme_defaults.STATUS_WARNING,
                                              update=_on_theme_color_update)
    status_error_color: FloatVectorProperty(name='Invalid Status', **public_color,
                                            default=theme_defaults.STATUS_ERROR,
                                            update=_on_theme_color_update)

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
    def _on_force_show_update(context):
        from ..utils.ui_draw_sync import (
            invalidate_panel_pause_cache,
            tag_gesture_ui_regions,
        )
        invalidate_panel_pause_cache()
        tag_gesture_ui_regions()

    @staticmethod
    def draw_text_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        draw = pref.draw_property

        col = layout.box().column(align=True)
        col.prop(draw, 'element_draw_child_icon')
        col.prop(draw, 'element_draw_property_toggle_icon')
        view = bpy.context.preferences.view
        if getattr(getattr(view, 'bl_rna', None), 'properties', {}).get(
                'show_number_arrows'
        ) is not None:
            col.prop(view, 'show_number_arrows', text='Numeric Input Arrows')
        col.prop(draw, 'text_gpu_draw_size')
        cr = col.row(align=True)
        cr.prop(draw, 'text_gpu_draw_radius')
        col.separator()
        col.prop(draw, 'element_extension_item_offset')
        col.separator()
        col.prop(draw, 'margin')
        col.prop(draw, 'layout_margin')
        col.separator()
        col.prop(draw, 'gesture_point_name_size')
        col.prop(draw, 'line_width')
        col.prop(draw, 'outline_width')
        col.prop(draw, 'dividing_line_height')

    @staticmethod
    def draw_color_property(layout: bpy.types.UILayout):
        pref = get_pref()
        draw = pref.draw_property
        box = layout.box()

        preset = box.column(align=True)
        preset.label(text='Overlay Theme')
        preset.prop(draw, 'theme_preset', text='')
        if draw.theme_preset == 'CUSTOM':
            preset.label(text='Custom colors are stored with preferences')
        box.separator()

        bb = box.column(align=True)
        bb.label(text='Surfaces')
        bb.prop(draw, 'overlay_background_color')
        bb.prop(draw, 'overlay_header_color')

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
        bb.prop(draw, 'background_int_color')
        bb.prop(draw, 'background_int_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'background_float_color')
        bb.prop(draw, 'background_float_active_color')

        bb = box.column(align=True)
        bb.label(text='Interaction')
        bb.prop(draw, 'interaction_hover_color')
        bb.prop(draw, 'interaction_pressed_color')

        bb = box.column(align=True)
        bb.prop(draw, 'text_default_color')
        bb.prop(draw, 'text_active_color')
        bb.prop(draw, 'text_disabled_color')

        bb = box.column(align=True)
        bb.prop(draw, 'trajectory_mouse_color')
        bb.prop(draw, 'trajectory_gesture_color')

        bb = box.column(align=True)
        bb.prop(draw, 'dividing_line_color')
        bb.prop(draw, 'outline_color')
        bb.prop(draw, 'outline_active_color')

        bb = box.column(align=True)
        bb.prop(draw, 'status_disabled_color')
        bb.prop(draw, 'status_warning_color')
        bb.prop(draw, 'status_error_color')
