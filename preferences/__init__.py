import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import AddonPreferences, PropertyGroup, UILayout

from . import system
from .system import SystemItem
from ..ops.crud.systems_crud import SystemCURD
from ..ops.crud.ui_element_crud import ElementCRUD
from ..ui.template_list import UiElementList, UiSystemList
from ..utils.public import PublicClass, PublicData


class DrawPreferences(PublicClass):

    def draw_preferences(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        sp = layout.split(factor=self.ui_prop.system_element_split_factor)

        col = sp.column()
        sub_row = col.row(align=True)
        self.draw_ui_system_crud(context, sub_row)
        sub_col = sub_row.column(align=True)
        self.draw_ui_system(context, sub_col)
        sys_item = self.active_system
        if sys_item and sys_item.is_draw_key:
            self.active_system.key.draw_key(sub_col)

        col = sp.column()
        sub_row = col.row(align=True)
        act = self.active_ui_element
        if act:
            self.active_ui_element.draw_active_ui_element_parameter(col)

        self.draw_ui_element(context, sub_row)
        self.draw_ui_element_crud(context, sub_row)
        if self.active_system:
            self.active_system.draw_ui_layout(col.box())

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
        DrawPreferences.draw_crud(layout, SystemCURD)

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
        DrawPreferences.draw_crud(layout, ElementCRUD)
        # layout.operator(ElementCRUD.Refresh.bl_idname, text='', icon='FILE_REFRESH')
        #     op = col.operator(cls.MoveRelation.bl_idname, text='', icon='GRIP')

    @staticmethod
    def draw_crud(layout, cls) -> 'UILayout':
        is_element = (cls == ElementCRUD)
        column = layout.column(align=True)
        add = column.operator(cls.Add.bl_idname, icon='ADD', text='')
        column.operator(cls.Copy.bl_idname, icon='COPYDOWN', text='')
        column.operator(cls.Del.bl_idname, icon='REMOVE', text='')
        if is_element:
            add.ui_type = 'UI_LAYOUT'
            sel_add = column.operator(cls.Add.bl_idname, icon='RNA_ADD', text='')
            sel_add.ui_type = 'SELECT_STRUCTURE'
        column.separator()
        column.operator(cls.Move.bl_idname, text='', icon='SORT_DESC').is_next = False
        column.operator(cls.Move.bl_idname, text='', icon='SORT_ASC').is_next = True
        column.separator()
        return column

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
                                      max=250)


class PreferencesProperty:
    """inherited to addon preferences by this class
    """
    systems: CollectionProperty(name='UI Collection Items',
                                description='Element Item',
                                type=SystemItem
                                )
    active_index: IntProperty(name='gesture active index')
    enabled_systems: BoolProperty(name='Use all Systems')
    ui_property: PointerProperty(name='Ui Property',
                                 type=UiProperty,
                                 description="Control the display settings on the addon interface")


class GesturePreferences(PublicClass,
                         PreferencesProperty,
                         AddonPreferences):
    bl_idname = PublicData.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        DrawPreferences().draw_preferences(context, layout)

    @classmethod
    def register_pref(cls):
        for item in cls.pref_().systems:
            item.register_system()

    @classmethod
    def unregister_pref(cls):
        for item in cls.pref_().systems:
            item.unregister_system()


classes_tuple = (
    UiProperty,
    GesturePreferences,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    system.register()
    register_class()


def unregister():
    system.unregister()
    unregister_class()
