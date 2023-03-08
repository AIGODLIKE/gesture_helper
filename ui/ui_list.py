import bpy.utils
from bpy.types import UIList

from .utils import space_layout


def draw_default_filter(self, layout):
    sp = layout.split()
    row = sp.row(align=True)
    row.prop(self, 'filter_name', text='')
    row.prop(self, 'use_filter_invert', icon='ARROW_LEFTRIGHT')

    row = sp.row(align=True)
    row.pref(self, 'use_filter_sort_alpha', icon='ICON_NONE', text='')
    row.pref(self,
             'use_filter_sort_reverse',
             icon='UILST_FLT_SORT_REVERSE' if self.use_filter_sort_reverse else 'ICON_SORT_ASC',
             text=''
             )


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
        from ..utils.preferences import GestureAddonPreferences
        col = layout.column()
        draw_default_filter(self, col)

        row = col.row(align=True)

        row.operator(GestureAddonPreferences.Import.bl_idname,
                     text='',
                     icon='PRESET',
                     )

        row.operator(GestureAddonPreferences.Import.bl_idname,
                     icon='IMPORT',
                     )

        row.operator(GestureAddonPreferences.Export.bl_idname,
                     icon='EXPORT',
                     )


class DrawUIElement(UIList):
    bl_idname = 'DRAW_UL_ui_element'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item,
                  icon, active_data, active_property, index, flt_flag):
        layout = space_layout(layout, 1, level=item.level)
        row = layout.row(align=True)
        row.prop(
            item,
            'name',
            text='',
        )
        row.separator()
        row.label(text=str(item.parent))
        row.label(text=str(item.level))

class_tuple = (
    DrawElement,
    DrawUIElement,
)
register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
