import bpy

from ..utils.utils import PublicClass
from ..utils.gesture import ElementGroup
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

    def draw_crud(self, layout, cls):
        col = layout.column(align=True)
        col.operator(cls.Add.bl_idname, text='', icon='ADD')
        col.operator(cls.Del.bl_idname, text='', icon='REMOVE')
        col.operator(cls.Copy.bl_idname, text='', icon='COPYDOWN')

        col.separator()

        col.operator(cls.Move.bl_idname, text='', icon='SORT_DESC').is_next = False
        col.operator(cls.Move.bl_idname, text='', icon='SORT_ASC').is_next = True

    def draw_element_item(self, layout):
        row = layout.row(align=True)
        from ..utils.preferences import GestureAddonPreferences
        self.draw_crud(row, GestureAddonPreferences)

        row.template_list(DrawElement.bl_idname,
                          DrawElement.bl_idname,
                          self.pref,
                          'gesture_element_collection_group',
                          self.pref,
                          'active_index'
                          )

    def draw_element_ui_list(self, layout):
        row = layout.row(align=True)
        self.draw_crud(row, ElementGroup)

        if self.pref.active_element:
            row.template_list(DrawUIElement.bl_idname,
                              DrawUIElement.bl_idname,
                              self.pref.active_element,
                              'ui_items_collection_group',
                              self.pref.active_element,
                              'active_index'
                              )
        else:
            row.label(text="Not Gesture Element")

    def draw_element_ui_property(self):
        ...

    def draw_preferences(self, layout):

        for key, value in self.pref.rna_type.properties.items():
            layout.prop(self, key)


def register():
    ...


def unregister():
    ...
