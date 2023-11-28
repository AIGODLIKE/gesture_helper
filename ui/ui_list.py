import bpy
from bpy.types import UIList

from ..utils.public import PublicProperty
from ..utils.public_ui import icon_two


class GestureUIList(UIList):
    bl_idname = 'DRAW_UL_gesture_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout)


class ElementUIList(UIList,
                    PublicProperty):
    bl_idname = 'DRAW_UL_element_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout.column(align=True))

    def draw_filter(self, context, layout):
        column = layout.column(align=True)

        row = column.row(align=True)
        prop = self.draw_property
        row.prop(prop, 'element_split_factor')
        icon = icon_two(prop.element_show_enabled_button, 'HIDE')
        row.prop(prop, 'element_show_enabled_button', icon=icon)
        icon = icon_two(prop.element_show_left_side, 'ALIGN')
        row.prop(prop, 'element_show_left_side', icon=icon)

        row = column.row(align=True)
        row.prop(prop, 'element_debug_mode', icon='GHOST_ENABLED')
        row.prop(prop, 'element_debug_draw_gpu_mode', icon='INFO')
