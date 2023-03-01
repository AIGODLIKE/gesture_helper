import bpy

from ..utils.utils import PublicClass
from ..utils.gesture import ElementItem
from .ui_list import DrawElement, DrawUIElement


class DrawPreferences(PublicClass):

    def __init__(self, layout: bpy.types.UILayout, draw=True):
        self.layout = layout
        if draw:
            self.draw_pref()

    def draw_pref(self):
        layout = self.layout
        row = layout.split()
        self.draw_element_item(row)

        self.draw_element_ui_list(row)

    def draw_element_item(self, layout):
        row = layout.row(align=True)
        from ..utils.preferences import GestureAddonPreferences
        col = row.column(align=True)
        col.operator(GestureAddonPreferences.Add.bl_idname, text='', icon='ADD')
        col.operator(GestureAddonPreferences.Del.bl_idname, text='', icon='REMOVE')
        col.operator(GestureAddonPreferences.Copy.bl_idname, text='', icon='COPYDOWN')

        col.separator()

        col.operator(GestureAddonPreferences.Move.bl_idname, text='', icon='SORT_DESC')
        col.operator(GestureAddonPreferences.Move.bl_idname, text='', icon='SORT_ASC')

        row.template_list(DrawElement.bl_idname,
                          DrawElement.bl_idname,
                          self.pref,
                          'gesture_element_items',
                          self.pref,
                          'active_index'
                          )

    def draw_element_ui_list(self, layout):
        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator(ElementItem.Add.bl_idname, text='', icon='ADD')
        col.operator(ElementItem.Del.bl_idname, text='', icon='REMOVE')
        col.operator(ElementItem.Copy.bl_idname, text='', icon='COPYDOWN')

        col.separator()

        col.operator(ElementItem.Move.bl_idname, text='', icon='SORT_DESC')
        col.operator(ElementItem.Move.bl_idname, text='', icon='SORT_ASC')

        if self.pref.active_element:
            row.template_list(DrawUIElement.bl_idname,
                              DrawUIElement.bl_idname,
                              self.pref.active_element,
                              'ui_items',
                              self.pref.active_element,
                              'active_index'
                              )

        else:
            row.label(text="emm")

    def draw_element_ui_property(self):
        ...

    def draw_preferences(self, layout):

        for key, value in self.pref.rna_type.properties.items():
            layout.prop(self, key)


def register():
    ...


def unregister():
    ...
