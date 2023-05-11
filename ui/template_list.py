import bpy
from bpy_types import UIList

from ..utils.public import PublicClass
from ..utils.public.public_ui import PublicUi


class UiSystemList(UIList,
                   PublicClass,
                   PublicUi
                   ):
    bl_idname = 'DRAW_UL_ui_system'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw(layout)

    def draw_filter(self, context: 'bpy.context', layout: 'bpy.types.UILayout'):
        self.draw_default_ui_list_filter(self, layout)
        row = layout.row(align=True)
        row.prop(self.ui_prop, 'system_element_split_factor')
        row.prop(self.ui_prop, 'system_split_factor')


class UiElementList(UIList,
                    PublicClass,
                    PublicUi
                    ):
    bl_idname = 'DRAW_UL_ui_element'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw(layout.column(), 0)

    def draw_filter(self, context: 'bpy.context', layout: 'bpy.types.UILayout'):
        self.draw_default_ui_list_filter(self, layout)
        row = layout.row(align=True)
        row.prop(self.ui_prop, 'child_element_office')
        row.prop(self.ui_prop, 'element_split_factor')


classes_tuple = (
    UiSystemList,
    UiElementList
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
