import bpy.utils
from bpy.props import FloatProperty, IntProperty
from bpy.types import UIList

from ..utils.utils import PublicClass
from .utils import space_layout


class PublicUIList(UIList,
                   PublicClass
                   ):
    def draw_filter(self, context, layout):
        sp = layout.split()
        row = sp.row(align=True)
        row.prop(self, 'filter_name', text='')
        row.prop(self, 'use_filter_invert', icon='ARROW_LEFTRIGHT', text='')

        row = sp.row(align=True)
        row.prop(self, 'use_filter_sort_alpha', text='')
        row.prop(self,
                 'use_filter_sort_reverse',
                 icon='SORT_DESC' if self.use_filter_sort_reverse else 'SORT_ASC',
                 text=''
                 )


class DrawElement(PublicUIList):
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
        super().draw_filter(context, col)

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


class DrawUIElement(PublicUIList):
    bl_idname = 'DRAW_UL_ui_element'

    space_size: IntProperty(default=15,
                            min=1,
                            max=40,
                            name='间隔',
                            )

    def draw_item(self, context, layout: bpy.types.UILayout, data, item,
                  icon, active_data, active_property, index, flt_flag):
        layout = space_layout(layout, self.space_size, level=item.level)
        row = layout.row(align=True)
        row.prop(
            item,
            'name',
            text='',
        )
        row.separator()
        row.label(text=str(item.parent.name if item.parent else None))
        row.label(text=str(item.level))

    def draw_filter(self, context: 'bpy.context', layout: 'bpy.types.UILayout'):
        column = layout.column(align=True)
        super().draw_filter(context, column)
        column.prop(self, 'space_size')


class_tuple = (
    DrawElement,
    DrawUIElement,
)
register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
