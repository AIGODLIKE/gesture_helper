import bpy

from ..utils.utils import PublicClass
from ..utils.gesture import ElementGroup
from .ui_list import DrawElement, DrawUIElement


class PublicDraw(PublicClass):

    @staticmethod
    def draw_crud(layout, cls):
        is_ui_element = cls == ElementGroup
        col = layout.column(align=True)
        col.operator(cls.Add.bl_idname, text='', icon='ADD')
        col.operator(cls.Copy.bl_idname, text='', icon='COPYDOWN')
        col.operator(cls.Del.bl_idname, text='', icon='REMOVE')
        if is_ui_element:
            col.operator(cls.Add.bl_idname, text='', icon='RNA_ADD').is_select_structure = True  # 添加选择结构

        col.separator()

        col.operator(cls.Move.bl_idname, text='', icon='SORT_DESC').is_next = False
        if is_ui_element:
            op = col.operator(cls.MoveRelation.bl_idname, text='', icon='GRIP')

        col.operator(cls.Move.bl_idname, text='', icon='SORT_ASC').is_next = True

    def draw_properties(self, layout, point):
        col = layout.column(align=True)
        if self.is_debug and point:
            for i in point.bl_rna.properties:
                col.prop(point, i.identifier)

    def draw_preferences(self, layout):
        for key, value in self.pref.rna_type.properties.items():
            layout.prop(self, key)


class DrawPreferences(PublicDraw):

    def __init__(self, layout: bpy.types.UILayout, draw=True):
        self.layout = layout
        if draw:
            self.draw_pref()

    def draw_pref(self):
        layout = self.layout
        layout.prop(self.pref, 'is_debug')
        row = layout.split()

        self.draw_element_collection_left(row)

        self.draw_element_ui_collection_right(row)

    def draw_element_collection_left(self, layout):
        row = layout.row(align=True)
        from ..utils.preferences import GestureAddonPreferences
        self.draw_crud(row, GestureAddonPreferences)
        row = row.column()
        row.template_list(DrawElement.bl_idname,
                          DrawElement.bl_idname,
                          self.pref,
                          'gesture_element_collection_group',
                          self.pref,
                          'active_index'
                          )
        self.draw_properties(row, self.active_element)

    def draw_element_ui_collection_right(self, layout):
        row = layout.row(align=True)

        if self.pref.active_element:
            col = row.column()
            col.template_list(DrawUIElement.bl_idname,
                              DrawUIElement.bl_idname,
                              self.pref.active_element,
                              'ui_items_collection_group',
                              self.pref.active_element,
                              'active_index'
                              )
            self.draw_element_ui_property(col)
        else:
            row.label(text="Not Gesture Element")
        self.draw_crud(row, ElementGroup)

    def draw_element_ui_property(self, layout):
        act = self.active_ui_element
        if act and self.is_debug:
            layout.label(text='parent\t\t' + str(act.parent.name if act.parent else None))
            layout.label(text='child\t\t' + str(list(i.name for i in act.child)))
            layout.label(text='children\t\t' + str(list(i.name for i in act.children)))
        self.draw_properties(layout, act)


def register():
    ...


def unregister():
    ...
