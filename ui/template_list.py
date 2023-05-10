import bpy
from bpy_types import UIList

from ..utils.public import PublicClass


class UiSystemList(UIList,
                   PublicClass):
    bl_idname = 'DRAW_UL_ui_system'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        layout.prop(item, 'name')
        layout.prop(item, 'system_type')


class UiElementList(UIList,
                    PublicClass):
    bl_idname = 'DRAW_UL_ui_element'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        layout.prop(item, 'name')
        p = item.parent.name if item.parent else 'None'
        layout.label(text=p)
        layout.label(text=str(c.name for c in item.children))
        layout.prop(item, 'ui_layout_type')


classes_tuple = (
    UiSystemList,
    UiElementList
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
