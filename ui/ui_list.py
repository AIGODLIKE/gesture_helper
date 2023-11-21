import bpy
from bpy_types import UIList

from ..utils.public import PublicProperty


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
        row = layout.row()
        prop = self.draw_property
        row.prop(prop, 'element_split_factor')
        row.prop(prop, 'element_show_enabled_button')
        row.prop(prop, 'element_debug_mode')
        row.prop(prop, 'element_show_left_side')
