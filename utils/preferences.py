import bpy
from bpy.props import CollectionProperty, IntProperty, BoolProperty, PointerProperty, FloatProperty
from bpy.types import AddonPreferences
from bpy_types import PropertyGroup

from .public import PublicClass, PublicData
from .system import SystemItem
from ..ops.crud.systems_crud import SystemOps
from ..ops.crud.ui_element_crud import ElementOps
from ..ui.template_list import UiSystemList, UiElementList


class DrawPreferences(PublicClass):

    def draw_preferences(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        sp = layout.split(factor=self.ui_prop.system_element_split_factor)

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
        # TODO
        DrawPreferences.draw_crud(layout, SystemOps)

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
        DrawPreferences.draw_crud(layout, ElementOps)
        layout.operator(ElementOps.Refresh.bl_idname, text='', icon='FILE_REFRESH')
        #     op = col.operator(cls.MoveRelation.bl_idname, text='', icon='GRIP')

    @staticmethod
    def draw_crud(layout, cls):
        column = layout.column(align=True)
        column.operator(cls.Add.bl_idname, icon='ADD', text='')
        column.operator(cls.Copy.bl_idname, icon='COPYDOWN', text='')
        column.operator(cls.Del.bl_idname, icon='REMOVE', text='')
        column.separator()
        column.operator(cls.Move.bl_idname, text='', icon='SORT_DESC').is_next = False
        column.operator(cls.Move.bl_idname, text='', icon='SORT_ASC').is_next = True
        column.separator()

    def draw_top_bar(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...


class UiProperty(PropertyGroup):
    default_factor = {
        'min': 0.15,
        'max': 0.9,
    }
    system_element_split_factor: FloatProperty(name="System Element Left Right Split Factor",
                                               default=0.5,
                                               **default_factor)

    system_split_factor: FloatProperty(name="System Item Split",
                                       default=0.5,
                                       **default_factor)

    element_split_factor: FloatProperty(name="Element Item Split",
                                        default=0.2,
                                        **default_factor,
                                        )
    child_element_office: IntProperty(name="UI Element Child Office Factor",
                                      default=50,
                                      min=10,
                                      max=100)


class PreferencesProperty:
    """inherited to addon preferences by this class
    """
    systems: CollectionProperty(name='UI Collection Items',
                                description='Element Item',
                                type=SystemItem
                                )
    active_index: IntProperty(name='gesture active index')
    enabled_systems: BoolProperty(name='Use all Systems')
    ui_property: PointerProperty(type=UiProperty)


class GesturePreferences(PublicClass, PreferencesProperty, AddonPreferences):
    bl_idname = PublicData.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        DrawPreferences().draw_preferences(context, layout)


classes_tuple = (
    UiProperty,
    GesturePreferences,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
