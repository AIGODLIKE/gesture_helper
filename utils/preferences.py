import bpy
from bpy.props import CollectionProperty, IntProperty
from bpy.types import AddonPreferences

from ..ui.template_list import UiSystemList, UiElementList
from .gesture_system import SystemItem
from .public import PublicClass, PublicData


class DrawPreferences(PublicClass):

    def draw_preferences(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        self.draw_ui_system(context, layout)
        self.draw_ui_element(context, layout)

    def draw_ui_system(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        pref = self.pref
        layout.template_list(
            UiSystemList.bl_idname,
            UiSystemList.bl_idname,
            pref,
            'ui_system',
            pref,
            'active_index', )

    def draw_ui_system_crud(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...

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

    def draw_ui_element_crud(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...

    def draw_top_bar(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...


class PreferencesProperty:
    """inherited to addon preferences by this class
    """
    ui_system: CollectionProperty(name='UI Collection Items',
                                  description='Element Item',
                                  type=SystemItem
                                  )
    active_index: IntProperty(name='gesture active index')


class GesturePreferences(PublicClass, PreferencesProperty, AddonPreferences):
    bl_idname = PublicData.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.bl_idname)
        layout.label(text='emmmoiasejoif')
        DrawPreferences().draw_preferences(context, layout)


classes_tuple = (
    GesturePreferences,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
