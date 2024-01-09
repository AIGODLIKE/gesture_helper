import bpy.utils
from bpy.props import CollectionProperty, IntProperty, BoolProperty, PointerProperty, FloatProperty, EnumProperty, \
    FloatVectorProperty
from bpy.types import AddonPreferences, PropertyGroup

from . import gesture
from .gesture.element.element_property import ElementAddProperty
from .public import ADDON_NAME, get_pref, PublicProperty, get_debug
from .public_ui import icon_two
from ..ops import export_import
from bpy.app.translations import pgettext as _
AddElementProperty = type('Add Element Property', (ElementAddProperty, PropertyGroup), {})
public_color = {"size": 4, "subtype": 'COLOR', "min": 0, "max": 1}


class DrawProperty(PropertyGroup):
    element_split_factor: FloatProperty(name=_('Split Coefficient'), default=0.09, max=0.95, min=0.01)
    element_show_enabled_button: BoolProperty(name=_('Display Enable/Disable Button'), default=True)
    element_show_left_side: BoolProperty(name=_('Display on the Left'), default=False)

    text_gpu_draw_size: IntProperty(name=_('Font Size'), description=_('Text Size for GPU Rendering'), default=20, min=5, max=120)
    text_gpu_draw_radius: IntProperty(name=_('Corner Radius Size'), description=_('Corner Radius Size for GPU Rendering'), default=10)
    text_gpu_draw_margin: IntProperty(name=_('Margin'), description=_('Margin Size for GPU Rendering'), default=7)
    line_width: IntProperty(name=_('Line Width'), description=_('Line Width Size for GPU Rendering'), default=5, min=2, max=114)

    background_default_color: FloatVectorProperty(name=_('Default Background Color'), **public_color, default=(.05, .05, .05, 1))
    background_active_color: FloatVectorProperty(name=_('Active Background Color'), **public_color, default=(.2, .2, .2, 1))
    text_default_color: FloatVectorProperty(name=_('Default Text Color'), **public_color, default=(.8, .8, .8, 1))
    text_active_color: FloatVectorProperty(name=_('Active Text Color'), **public_color, default=(1, 1, 1, 1))
    mouse_trajectory_color: FloatVectorProperty(name=_('Mouse Trail Color'), **public_color, default=(.1, .9, 1, 1))
    gesture_trajectory_color: FloatVectorProperty(name=_('Gesture Trail Color'), **public_color, default=(0, .7, .9, 1))


class DebugProperty(PropertyGroup):
    debug_mode: BoolProperty(name=_('Debug Mode'), default=False)
    debug_key: BoolProperty(name=_('Debug Shortcut'), default=False)
    debug_draw_gpu_mode: BoolProperty(name=_('Debug Drawing in GPU Mode'), default=False)


class OtherProperty(PropertyGroup):
    auto_update_element_operator_properties: BoolProperty(name=_('Auto-Update Action Properties'))
    is_move_element: BoolProperty(
        default=False,
        description="""Move Element: the entire element requires only the move operator to be available""",
        options={"SKIP_SAVE"})
    auto_backups: BoolProperty(
        name='Automatic Backup',
        description="Automatically save data every time the plugin is deactivated, to avoid data loss due to accidental operations. The automatic save path is in the 'auto_backups' folder of the plugin's path",
        default=True,
    )


class GestureProperty(PropertyGroup):
    @staticmethod
    def gen_gesture_prop(default, subtype='PIXEL'):
        return {'max': 114514, 'default': default, 'subtype': subtype, 'min': 20}

    def update_threshold_confirm(self, context):
        if self.threshold > self.threshold_confirm:
            self['threshold_confirm'] = self.threshold_confirm + 20

    timeout: IntProperty(name=_('Gesture TimeOut(ms)'), **gen_gesture_prop(300, 'TIME'))
    radius: IntProperty(name=_('Gesture Radius'), **gen_gesture_prop(150))
    threshold: IntProperty(name=_('Threshold'), **gen_gesture_prop(30))
    threshold_confirm: IntProperty(name=_('Confirm Threshold') ,**gen_gesture_prop(50))

    automatically_handle_conflicting_keymaps: BoolProperty(name=_('Automatically handle conflicting shortcuts when setting key mappings'), default=True)
    show_gesture_keymaps: BoolProperty(name=_('Display Gesture Item Shortcuts'))

    @staticmethod
    def draw(layout):
        pref = get_pref()
        g = pref.gesture_property
        draw = pref.draw_property
        other = pref.other_property
        debug = pref.debug_property

        row = layout.row()
        column = row.column(align=True)
        column.prop(g, 'automatically_handle_conflicting_keymaps')
        column.prop(other, 'auto_backups')
        column.separator()

        column.label(text='Debug')
        column.prop(debug, 'debug_mode')
        column.prop(debug, 'debug_key')
        column.prop(debug, 'debug_draw_gpu_mode')

        col = row.column(align=True)
        col.label(text='Gesture:')
        col.prop(draw, 'text_gpu_draw_size')
        col.prop(draw, 'text_gpu_draw_radius')
        col.prop(draw, 'text_gpu_draw_margin')
        col.prop(draw, 'line_width')
        col.prop(g, 'timeout')
        col.separator()
        col.prop(g, 'radius')
        col.prop(g, 'threshold')
        col.prop(g, 'threshold_confirm')
        col.label(text='Color:')
        row = col.row(align=True)
        col.prop(draw, 'background_default_color')
        col.prop(draw, 'background_active_color')
        col.prop(draw, 'text_default_color')
        col.prop(draw, 'text_active_color')
        col.prop(draw, 'mouse_trajectory_color')
        col.prop(draw, 'gesture_trajectory_color')


class ElementDraw:
    @staticmethod
    def draw_property(layout: 'bpy.types.UILayout') -> None:
        pref = get_pref()
        act = pref.active_element
        prop = pref.draw_property
        if act:
            if not prop.element_show_left_side:
                act.draw_item_property(layout)
            if get_debug():
                act.draw_debug(layout)
        else:
            layout.label(text='Please select or add a gesture element')

    @staticmethod
    def draw_element_cure(layout: 'bpy.types.UILayout', cls) -> None:
        column = layout.column(align=True)
        column.operator(
            cls.COPY.bl_idname,
            icon='COPYDOWN',
            text=''
        )
        column.operator(
            cls.REMOVE.bl_idname,
            icon='REMOVE',
            text=''
        )

    @staticmethod
    def draw_element_add_property(layout: 'bpy.types.UILayout') -> None:
        from .enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
        from .gesture.element import ElementCURE

        pref = get_pref()
        add = pref.add_element_property

        relationship = add.relationship
        add_child = add.is_have_add_child

        split = layout.split(factor=.4)

        row = split.row(align=True)
        row.label(text='Add Element Relationship')
        row.prop(add, 'relationship', expand=True)

        sub_row = split.row(align=True)
        sub_row.enabled = add_child

        if add_child:
            element_row = sub_row.row(align=True)
            element_row.separator()
            element_row.label(text='Add Item:')
            for i, n, d in ENUM_ELEMENT_TYPE:
                if i != 'SELECTED_STRUCTURE':
                    ops = element_row.operator(ElementCURE.ADD.bl_idname, text=n)
                    ops.element_type = i
                    ops.relationship = relationship
            element_row.separator()
            for i, n, d in ENUM_SELECTED_TYPE:
                ops = element_row.operator(ElementCURE.ADD.bl_idname, text=n)
                ops.element_type = 'SELECTED_STRUCTURE'
                ops.selected_type = i
                ops.relationship = relationship
        else:
            sub_row.row(align=True).label(text="Cannot add a child to 'Operator'")


class GestureDraw:

    @staticmethod
    def draw_gesture_cure(layout: 'bpy.types.UILayout') -> None:
        from .gesture import gesture_cure
        GestureDraw.public_cure(layout, gesture_cure.GestureCURE)

    @staticmethod
    def draw_gesture_key(layout) -> None:
        pref = get_pref()
        active = pref.active_gesture
        if active:
            column = layout.column()
            column.active = active.is_enable
            active.draw_key(column)
        else:
            layout.label(text='Not Select Gesture')

    @staticmethod
    def draw_gesture_item(layout: bpy.types.UILayout) -> None:
        from ..ui.ui_list import GestureUIList
        pref = get_pref()
        row = layout.row(align=True)
        GestureDraw.draw_gesture_cure(row)
        column = row.column(align=True)
        column.template_list(
            GestureUIList.bl_idname,
            GestureUIList.bl_idname,
            pref,
            'gesture',
            pref,
            'index_gesture',
        )
        ag = pref.active_gesture
        if ag is not None:
            column.prop(ag, 'description')
        GestureDraw.draw_gesture_key(column)

    @staticmethod
    def draw_element(layout: bpy.types.UILayout) -> None:
        from ..ui.ui_list import ElementUIList
        pref = get_pref()
        ag = pref.active_gesture
        if ag:
            column = layout.column()

            ElementDraw.draw_element_add_property(column)
            row = column.row(align=True)

            sub_column = row.column()
            sub_column.template_list(
                ElementUIList.bl_idname,
                ElementUIList.bl_idname,
                ag,
                'element',
                ag,
                'index_element',
            )
            ElementDraw.draw_property(sub_column)

            GestureDraw.draw_element_cure(row)
        else:
            layout.label(text='Please add or select a gesture')

    @staticmethod
    def draw_element_cure(layout: bpy.types.UILayout) -> None:
        from .gesture import ElementCURE
        GestureDraw.public_cure(layout, ElementCURE)

    @staticmethod
    def public_cure(layout, cls) -> None:
        is_element = cls.__name__ == 'ElementCURE'
        pref = get_pref()
        draw_property = pref.draw_property
        other = pref.other_property

        column = layout.column(align=True)
        if is_element:
            ElementDraw.draw_element_cure(column, cls)
            column.separator()
        else:
            column.operator(
                cls.ADD.bl_idname,
                icon='ADD',
                text=''
            )
            column.operator(
                cls.COPY.bl_idname,
                icon='COPYDOWN',
                text=''
            )
            column.operator(
                cls.REMOVE.bl_idname,
                icon='REMOVE',
                text=''
            )

        column.separator()

        column.operator(
            cls.SORT.bl_idname,
            icon='SORT_DESC',
            text=''
        ).is_next = False

        if is_element:
            moving = other.is_move_element
            icon = 'DOT' if moving else 'GRIP'

            row = column.row()
            if moving:
                move_item = cls.MOVE.move_item
                row.enabled = bool(move_item and not move_item.is_root)
            row.operator(
                cls.MOVE.bl_idname,
                icon=icon,
                text=''
            )
            if moving:
                column.operator(
                    cls.MOVE.bl_idname,
                    icon='CANCEL',
                    text=''
                ).cancel = True

        column.operator(
            cls.SORT.bl_idname,
            icon='SORT_ASC',
            text=''
        ).is_next = True

        if is_element:
            column.separator()
            icon = icon_two(draw_property.element_show_left_side, style='ALIGN')
            column.prop(draw_property, 'element_show_left_side', icon=icon, text='', emboss=False)
        else:
            column.separator()
            column.separator()

            import_id_name = export_import.Import.bl_idname
            column.operator(export_import.Export.bl_idname, icon='EXPORT', text='')
            column.operator(import_id_name, icon='ASSET_MANAGER', text='').preset_show = True
            column.operator(import_id_name, icon='IMPORT', text='').preset_show = False

    @staticmethod
    def draw_ui_gesture(layout):
        pref = get_pref()
        draw_property = pref.draw_property
        act = pref.active_element

        column = layout.column()
        split = column.split()

        if draw_property.element_show_left_side:  # 绘制属性在左侧
            box = split.box()
            if act:
                act.draw_item_property(box)
            else:
                box.label(text='Please select or add a gesture element')
        else:
            GestureDraw.draw_gesture_item(split)
        GestureDraw.draw_element(split)


class PropertyDraw:

    @staticmethod
    def draw_ui_property(layout):
        get_pref().gesture_property.draw(layout)


class PreferencesDraw(GestureDraw, PropertyDraw):

    # 绘制右边层
    def right_layout(self: bpy.types.Panel, context: bpy.context):
        pref = get_pref()

        column = self.layout.column(align=True)

        row = column.row(align=True)
        row.prop(pref, 'enabled', text='')
        row.prop(pref, 'show_page', expand=True)
        sub_column = column.column(align=True)
        if pref.is_show_gesture:
            sub_column.enabled = pref.enabled
        getattr(PreferencesDraw, f'draw_ui_{pref.show_page.lower()}')(sub_column)

    def left_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='left_layout')

    def bottom_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='bottom_layout')
        PreferencesDraw.exit(layout)

    def left_bottom_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='left_bottom_layout')
        PreferencesDraw.exit(layout)

    @staticmethod
    def exit(layout: 'bpy.types.UILayout') -> 'bpy.types.UILayout.operator':
        """退出按钮"""
        from ..ops.switch_ui import SwitchGestureWindow
        layout.alert = True
        return layout.operator(SwitchGestureWindow.bl_idname,
                               text='Exit',
                               icon='PANEL_CLOSE'
                               )


class GesturePreferences(PublicProperty,
                         AddonPreferences,
                         PreferencesDraw):
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name=_('Gesture Index'), update=lambda self, context: self.active_gesture.to_temp_kmi())

    draw_property: PointerProperty(type=DrawProperty)
    debug_property: PointerProperty(type=DebugProperty)
    other_property: PointerProperty(type=OtherProperty)
    gesture_property: PointerProperty(type=GestureProperty)
    add_element_property: PointerProperty(type=AddElementProperty)

    enabled: BoolProperty(
        name='Enable Gesture',
        description="""Enable or disable the entire system, mainly the keymap""",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())
    show_page: EnumProperty(name=_('Display Panel'), items=[('GESTURE', 'Gesture', ''), ('PROPERTY', 'Property', '')])

    @property
    def is_show_gesture(self):
        return self.show_page == 'GESTURE'

    @property
    def is_show_property(self):
        return self.show_page == 'PROPERTY'

    def draw(self, context):
        layout = self.layout
        self.right_layout(layout)


classes_list = (
    DrawProperty,
    DebugProperty,
    OtherProperty,
    GestureProperty,
    AddElementProperty,

    GesturePreferences,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(classes_list)


def register():
    gesture.register()
    register_classes()


def unregister():
    unregister_classes()
    gesture.unregister()
