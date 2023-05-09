import bpy
from bpy.props import CollectionProperty, IntProperty, BoolProperty
from bpy.types import AddonPreferences

from ..ops.crud.systems_crud import SystemAdd, SystemMove, SystemCopy, SystemDel
from ..ops.crud.ui_element_crud import ElementAdd, ElementMove, ElementDel, ElementCopy
from ..ui.template_list import UiSystemList, UiElementList
from .system import SystemItem
from .public import PublicClass, PublicData


class DrawPreferences(PublicClass):

    def draw_preferences(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        sp = layout.split(factor=0.5)

        sub_row = sp.row(align=True)
        self.draw_ui_system_crud(context, sub_row)
        self.draw_ui_system(context, sub_row)

        sub_row = sp.row(align=True)
        self.draw_ui_element(context, sub_row)
        self.draw_ui_element_crud(context, sub_row)

    def draw_ui_system(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        pref = self.pref
        layout.template_list(
            UiSystemList.bl_idname,
            UiSystemList.bl_idname,
            pref,
            'systems',
            pref,
            'active_index', )

    @staticmethod
    def draw_ui_system_crud(context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        column = layout.column(align=True)
        column.operator(SystemAdd.bl_idname, icon='ADD', text='')
        column.operator(SystemCopy.bl_idname, icon='COPYDOWN', text='')
        column.operator(SystemDel.bl_idname, icon='REMOVE', text='')
        column.separator()
        column.operator(SystemMove.bl_idname, text='', icon='SORT_DESC').is_next = False
        column.operator(SystemMove.bl_idname, text='', icon='SORT_ASC').is_next = True

    def draw_ui_element(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        pref = self.pref
        system = pref.active_system
        if system:
            layout.template_list(
                UiElementList.bl_idname,
                UiElementList.bl_idname,
                system,
                'ui_element',
                system,
                'active_index', )
        else:
            layout.label(text='Select or new element')

    @staticmethod
    def draw_ui_element_crud(context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        column = layout.column(align=True)
        column.operator(ElementAdd.bl_idname, icon='ADD', text='')
        column.operator(ElementCopy.bl_idname, icon='COPYDOWN', text='')
        column.operator(ElementDel.bl_idname, icon='REMOVE', text='')
        column.separator()
        column.operator(ElementMove.bl_idname, text='', icon='SORT_DESC').is_next = False
        column.operator(ElementMove.bl_idname, text='', icon='SORT_ASC').is_next = True

        #     op = col.operator(cls.MoveRelation.bl_idname, text='', icon='GRIP')

    def draw_top_bar(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...


class PreferencesProperty:
    """inherited to addon preferences by this class
    """
    systems: CollectionProperty(name='UI Collection Items',
                                description='Element Item',
                                type=SystemItem
                                )
    active_index: IntProperty(name='gesture active index')
    enabled_systems: BoolProperty(name='Use all Systems')


class GesturePreferences(PublicClass, PreferencesProperty, AddonPreferences):
    bl_idname = PublicData.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        DrawPreferences().draw_preferences(context, layout)


classes_tuple = (
    GesturePreferences,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
