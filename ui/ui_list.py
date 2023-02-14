import bpy.utils
from bpy.types import UIList


class DrawUIList(UIList):
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
        

def register():
    bpy.utils.register_class(DrawUIList)


def unregister():
    bpy.utils.unregister_class(DrawUIList)
