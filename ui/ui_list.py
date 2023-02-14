import bpy.utils
from bpy.types import UIList


class DrawElement(UIList):
    bl_idname = 'DRAW_UL_element'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item,
                  icon, active_data, active_property, index, flt_flag):
        row = layout.row(align=True)
        row.prop(
            item,
            'name',
            text='',
        )
        row.separator()
        row.label(text='emm')

    def draw_filter(self, context: 'bpy.context', layout: 'bpy.types.UILayout'):
        from ..utils.preferences import GestureAddon
        row = layout.row(align=True)

        row.operator(GestureAddon.Import.bl_idname,
                     text='',
                     icon='PRESET',
                     )

        row.operator(GestureAddon.Import.bl_idname,
                     icon='IMPORT',
                     )

        row.operator(GestureAddon.Export.bl_idname,
                     icon='EXPORT',
                     )


class DrawUIElement(UIList):
    bl_idname = 'DRAW_UL_ui_element'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item,
                  icon, active_data, active_property, index, flt_flag):
        row = layout.row(align=True)
        row.prop(
            item,
            'name',
            text='',
        )
        row.separator()
        row.label(text='emm')


class_tuple = (
    DrawElement,
    DrawUIElement,
)
register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
