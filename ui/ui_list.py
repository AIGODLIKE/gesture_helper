import bpy

from ..utils.public import PublicProperty
from ..utils.public_ui import icon_two


class GestureUIList(bpy.types.UIList, PublicProperty):
    bl_idname = 'DRAW_UL_gesture_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout)

    def draw_filter(self, context, layout):
        column = layout.column(align=True)
        row = column.row(align=True)

        prop = self.draw_property
        row.prop(prop, 'gesture_show_enabled_button', icon=icon_two(prop.gesture_show_enabled_button, "HIDE"))
        row.prop(prop, 'gesture_show_keymap', icon="BLANK1")
        row.prop(prop, 'gesture_show_description', icon="INFO")

        row = column.row(align=True)
        row.active = prop.gesture_show_keymap
        row.prop(prop, "gesture_keymap_split_factor")

        row = column.row(align=True)
        row.prop(prop, "gesture_remove_tips", icon="INFO_LARGE" if bpy.app.version >= (4, 3, 0) else "ERROR")
        row.prop(prop, "enable_name_translation", icon="BLANK1")


class ElementUIList(bpy.types.UIList, PublicProperty):
    bl_idname = 'DRAW_UL_element_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout.column(align=True))

    def draw_filter(self, context, layout):
        from ..element.element_cure import ElementCURE
        column = layout.column(align=True)

        row = column.row(align=True)
        prop = self.draw_property
        row.prop(prop, 'element_split_factor')
        icon = icon_two(prop.element_show_enabled_button, 'HIDE')
        row.prop(prop, 'element_show_enabled_button', icon=icon)
        icon = icon_two(prop.element_show_left_side, 'ALIGN')
        row.prop(prop, 'element_show_left_side', icon=icon)

        row = column.row(align=True)
        icon = icon_two(prop.element_show_icon, 'HIDE')
        row.prop(prop, 'element_show_icon', icon=icon)

        debug = self.debug_property
        row = column.row(align=True)
        row.prop(debug, 'debug_mode', icon='GHOST_ENABLED')
        row.prop(debug, 'debug_key', icon='GHOST_ENABLED')
        row.prop(debug, 'debug_draw_gpu_mode', icon='INFO')

        row = column.row(align=True)
        row.prop(prop, "element_remove_tips", icon="INFO_LARGE" if bpy.app.version >= (4, 3, 0) else "ERROR")
        row.operator(ElementCURE.SwitchShowChild.bl_idname)
        row.prop(prop, "enable_name_translation", icon="BLANK1")


class ImportPresetUIList(bpy.types.UIList,
                         PublicProperty):
    bl_idname = 'DRAW_UL_preset'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        layout.emboss = 'NONE'

        left = layout.row()
        left.alignment = 'LEFT'
        left.prop(item, 'selected', text=item.name, translate=False, icon='NONE')

        right = layout.row()
        right.alignment = 'RIGHT'
        right.prop(item, 'selected', icon=icon_two(item.selected, 'RESTRICT_SELECT'), text='')
