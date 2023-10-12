import bpy
from bpy.props import CollectionProperty, IntProperty, BoolProperty, PointerProperty, EnumProperty, FloatProperty
from bpy.types import AddonPreferences, PropertyGroup

from .system import SystemItem
from ..ops.systems_crud import SystemCURD
from ..ops.ui_element_crud import ElementCRUD
from ..public import PublicData, PublicProperty
from ..ui.template_list import UiSystemList, UiElementList


class UiProperty(PropertyGroup):
    """
    """
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


class GestureOpsShowProperty:

    @staticmethod
    def gen_gesture_prop(default, subtype='PIXEL'):
        return {'max': 514, 'default': default, 'subtype': subtype, 'min': 20}

    gesture_timeout: IntProperty(name='Gesture TimeOut', **gen_gesture_prop(300, 'TIME'))
    gesture_radius: IntProperty(name='Gesture Radius', **gen_gesture_prop(120))
    gesture_radius_threshold: IntProperty(name='Gesture Radius Threshold', **gen_gesture_prop(115))
    gesture_confirm_radius_threshold: IntProperty(name='Gesture Confirm Radius Threshold', **gen_gesture_prop(115))


class PropertyPreferences(PublicProperty, GestureOpsShowProperty):
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
    addon_show_type: EnumProperty(items=PublicData.ENUM_ADDON_SHOW_TYPE)


class DrawPreferences(PropertyPreferences):

    def draw_preferences(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        col = layout.column()
        row = col.row(align=True)
        row.prop(self.pref, 'addon_show_type', expand=True)
        draw_type = getattr(self.pref, 'addon_show_type', 'about')
        getattr(self, f'draw_{draw_type.lower()}')(context, col)

    def draw_about(self, context, layout):
        layout.label(text='about' + str(self))

    def draw_setting(self, context, layout):
        pref = self.pref
        layout.prop(pref, 'gesture_timeout')
        layout.prop(pref, 'gesture_radius')
        layout.prop(pref, 'gesture_radius_threshold')
        layout.prop(pref, 'gesture_confirm_radius_threshold')

    def draw_editor(self, context, layout):
        sp = layout.split(factor=self.ui_prop.system_element_split_factor)

        col = sp.column()
        sub_row = col.row(align=True)
        self.draw_ui_system_crud(context, sub_row)
        sub_col = sub_row.column(align=True)
        self.draw_ui_system(context, sub_col)
        sys_item = self.active_system
        if sys_item and sys_item.is_draw_key:
            self.active_system.keymap.draw_key(sub_col)

        col = sp.column()
        sub_row = col.row(align=True)
        act = self.active_ui_element
        if act:
            self.active_ui_element.draw_active_ui_element_parameter(col)

        self.draw_ui_element(context, sub_row)
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
        active_system = pref.active_system
        if active_system:
            layout.template_list(
                UiElementList.bl_idname,
                UiElementList.bl_idname,
                active_system,
                'ui_element',
                active_system,
                'active_index', )
            self.draw_ui_element_crud(context, layout)
        else:
            layout.label(text='Select or new element')

    @staticmethod
    def draw_ui_element_crud(context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        DrawPreferences.draw_crud(layout, ElementCRUD)
        # layout.operator(ElementCRUD.Refresh.bl_idname, text='', icon='FILE_REFRESH')
        #     op = col.operator(cls.MoveRelation.bl_idname, text='', icon='GRIP')

    @staticmethod
    def draw_crud(layout, cls) -> 'bpy.types.UILayout':
        is_element = (cls == ElementCRUD)
        column = layout.column(align=True)
        add = column.operator(cls.Add.bl_idname, icon='ADD', text='')
        column.operator(cls.Copy.bl_idname, icon='COPYDOWN', text='')
        column.operator(cls.Del.bl_idname, icon='REMOVE', text='')
        if is_element:
            act_system = cls.Add.pref_().active_system
            add.ui_type = 'GESTURE' if act_system.is_gesture_type else 'UI_LAYOUT'
            sel_add = column.operator(cls.Add.bl_idname, icon='RNA_ADD', text='')
            sel_add.ui_type = 'SELECT_STRUCTURE'
        column.separator()
        column.operator(cls.Move.bl_idname, text='', icon='SORT_DESC').is_next = False
        column.operator(cls.Move.bl_idname, text='', icon='SORT_ASC').is_next = True
        column.separator()
        return column

    def draw_top_bar(self, context: 'bpy.types.Context', layout: 'bpy.types.UILayout'):
        ...


class GestureHelperPreferences(DrawPreferences, AddonPreferences):
    bl_idname = PublicData.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        DrawPreferences().draw_preferences(context, layout)


classes_tuple = (
    UiProperty,
    GestureHelperPreferences,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    print('register', PublicData.G_ADDON_NAME)
    system.register()
    register_class()


def unregister():
    system.unregister()
    unregister_class()
    print('unregister', PublicData.G_ADDON_NAME)
