import os

import bpy.utils
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    PointerProperty,
    FloatProperty,
    EnumProperty,
    FloatVectorProperty,
    StringProperty)
from bpy.types import AddonPreferences, PropertyGroup

from . import gesture
from .element.element_property import ElementAddProperty
from .ops import export_import
from .utils.public import ADDON_NAME, get_pref, PublicProperty, get_debug
from .utils.public_ui import icon_two

AddElementProperty = type('Add Element Property', (ElementAddProperty, PropertyGroup), {})
public_color = {"size": 4, "subtype": 'COLOR', "min": 0, "max": 1}
isDebug = os.environ.get('USERNAME') in ("EM1", "emm")


class DrawProperty(PropertyGroup):
    element_split_factor: FloatProperty(name='拆分系数', default=0.09, max=0.95, min=0.01)
    element_show_enabled_button: BoolProperty(name='显示 启用/禁用 按钮', default=True)
    element_show_left_side: BoolProperty(name='显示在左侧', default=False)

    text_gpu_draw_size: IntProperty(name='文字大小', description='Gpu绘制的文字大小', default=20, min=5, max=120)
    text_gpu_draw_radius: IntProperty(name='圆角大小', description='Gpu绘制的圆角大小', default=10)
    text_gpu_draw_margin: IntProperty(name='Margin', description='Gpu绘制的Margin大小', default=7)
    line_width: IntProperty(name='线宽', description='Gpu绘制的线宽大小', default=5, min=2, max=114)

    background_operator_color: FloatVectorProperty(name='操作符颜色', **public_color,
                                                   default=[0.019382, 0.019382, 0.019382, 1.000000])
    background_child_color: FloatVectorProperty(name='子级颜色', **public_color,
                                                default=[0.431968, 0.222035, 0.650622, 1.000000])
    background_active_color: FloatVectorProperty(name='活动颜色', **public_color,
                                                 default=[0.738785, 0.776229, 1.000000, 1.000000])

    text_default_color: FloatVectorProperty(name='文字默认颜色', **public_color, default=(.8, .8, .8, 1))
    text_active_color: FloatVectorProperty(name='文字活动颜色', **public_color, default=(1, 1, 1, 1))
    mouse_trajectory_color: FloatVectorProperty(name='鼠标轨迹颜色', **public_color, default=(.1, .9, 1, 1))
    gesture_trajectory_color: FloatVectorProperty(name='手势轨迹颜色', **public_color, default=(0, .7, .9, 1))


class DebugProperty(PropertyGroup):
    debug_mode: BoolProperty(name='Debug模式', default=isDebug)
    debug_key: BoolProperty(name='Debug快捷键', default=isDebug)
    debug_draw_gpu_mode: BoolProperty(name='Debug绘制Gpu模式', default=isDebug)
    debug_export_import: BoolProperty(name='Debug导入导出', default=isDebug)


class OtherProperty(PropertyGroup):
    from .utils.public import ADDON_FOLDER
    auto_update_element_operator_properties: BoolProperty(name='自动更新操作属性')
    is_move_element: BoolProperty(
        default=False,
        description='移动元素 整个元素需要只有移动操作符可用',
        options={"SKIP_SAVE"})
    auto_backups: BoolProperty(
        name='启用自动备份',
        description='在每次注销插件时自动保存数据,避免误操作导致数据丢失, 自动保存的路径在插件路径的 "auto_backups" 文件夹',
        default=True,
    )
    enabled_backups_to_specified_path: BoolProperty(
        name='指定备份路径',
        description='备份到指定路径',
        default=False,
    )
    backups_path: StringProperty(
        name='备份路径',
        description='备份配置到指定路径',
        subtype='DIR_PATH',
        default=os.path.join(ADDON_FOLDER, 'auto_backups')
    )
    init_addon: BoolProperty(name="已初始化插件", default=False)


class GestureProperty(PropertyGroup):
    @staticmethod
    def gen_gesture_prop(default, subtype='PIXEL'):
        return {'max': 114514, 'default': default, 'subtype': subtype, 'min': 20}

    def update_threshold_confirm(self, _):
        if self.threshold > self.threshold_confirm:
            self['threshold_confirm'] = self.threshold_confirm + 20

    timeout: IntProperty(name='Gesture Timeout(ms)', **gen_gesture_prop(300, 'TIME'))
    radius: IntProperty(name='Gesture Radius', **gen_gesture_prop(150))
    threshold: IntProperty(name='Threshold', **gen_gesture_prop(30))
    threshold_confirm: IntProperty(name='Confirm Threshold', **gen_gesture_prop(50))

    show_gesture_keymaps: BoolProperty(name='显示手势项快捷键')

    @staticmethod
    def draw(layout):
        row = layout.row()
        row.use_property_split = True
        column = row.column(align=True)

        GestureProperty.draw_backups(column)
        column.separator()

        GestureProperty.draw_debug(column)

        col = row.column(align=True)
        GestureProperty.draw_gesture_property(col)
        GestureProperty.draw_color(col)

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        pref = get_pref()
        other = pref.other_property
        column = layout.column(heading="Auto Backups")

        box = column.box()
        box.prop(other, 'auto_backups')
        box.prop(other, 'enabled_backups_to_specified_path')
        if other.enabled_backups_to_specified_path:
            box.prop(other, 'backups_path')

        ops = column.operator("preferences.keymap_restore")
        ops.all = True
        # if other.auto_backups:
        # else:
        #     column.prop(other, 'auto_backups')

    @staticmethod
    def draw_debug(layout: bpy.types.UILayout):
        pref = get_pref()
        debug = pref.debug_property

        debug_box = layout.column(heading="Debug").box()
        debug_box.prop(debug, 'debug_mode')
        debug_box.prop(debug, 'debug_key')
        debug_box.prop(debug, 'debug_draw_gpu_mode')
        debug_box.prop(debug, 'debug_export_import')

    @staticmethod
    def draw_color(layout: bpy.types.UILayout):
        pref = get_pref()
        draw = pref.draw_property
        box = layout.box()
        box.label(text="Color")

        bb = box.column(heading="背景")
        bb.prop(draw, 'background_operator_color')
        bb.prop(draw, 'background_child_color')
        bb.prop(draw, 'background_active_color')

        bb = box.column(heading="字体")
        bb.prop(draw, 'text_default_color')
        bb.prop(draw, 'text_active_color')

        bb = box.column(heading="轨迹")
        bb.prop(draw, 'mouse_trajectory_color')
        bb.prop(draw, 'gesture_trajectory_color')

    @staticmethod
    def draw_gesture_property(layout: bpy.types.UILayout):
        pref = get_pref()

        col = layout.box()

        g = pref.gesture_property
        draw = pref.draw_property
        col.label(text='手势')
        col.prop(draw, 'text_gpu_draw_size')
        col.prop(draw, 'text_gpu_draw_radius')
        col.prop(draw, 'text_gpu_draw_margin')
        col.prop(draw, 'line_width')
        col.prop(g, 'timeout')
        col.separator()
        col.prop(g, 'radius')
        col.prop(g, 'threshold')
        col.prop(g, 'threshold_confirm')


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
            layout.label(text='请 选择或添加 一个手势元素')

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
        from .utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
        from .element import ElementCURE

        pref = get_pref()
        add = pref.add_element_property

        relationship = add.relationship
        add_child = add.is_have_add_child

        split = layout.split(factor=.4)

        row = split.row(align=True)
        row.label(text='添加元素关系')
        row.prop(add, 'relationship', expand=True)

        sub_row = split.row(align=True)
        sub_row.enabled = add_child

        if add_child:
            element_row = sub_row.row(align=True)
            element_row.separator()
            element_row.label(text='添加项:')
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
            sub_row.row(align=True).label(text="无法为 '操作符' 添加子级")


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
        from .ui.ui_list import GestureUIList
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
        from .ui.ui_list import ElementUIList
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
            layout.label(text='请添加或选择一个手势')

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
                box.label(text='请 选择或添加 一个手势元素')
        else:
            GestureDraw.draw_gesture_item(split)
        GestureDraw.draw_element(split)


class PropertyDraw:

    @staticmethod
    def draw_ui_property(layout):
        get_pref().gesture_property.draw(layout)


class PreferencesDraw(GestureDraw, PropertyDraw):

    # 绘制右边层
    def right_layout(self: bpy.types.Panel, _):
        pref = get_pref()

        column = self.layout.column(align=True)

        row = column.row(align=True)
        row.prop(pref, 'enabled', text='')
        row.prop(pref, 'show_page', expand=True)
        sub_column = column.column(align=True)
        if pref.is_show_gesture:
            sub_column.enabled = pref.enabled
        getattr(PreferencesDraw, f'draw_ui_{pref.show_page.lower()}')(sub_column)

    def left_layout(self: bpy.types.Panel, _):
        layout = self.layout
        layout.label(text='left_layout')

    def bottom_layout(self: bpy.types.Panel, _):
        layout = self.layout
        layout.label(text='bottom_layout')
        PreferencesDraw.exit(layout)

    def left_bottom_layout(self: bpy.types.Panel, _):
        layout = self.layout
        layout.label(text='left_bottom_layout')
        PreferencesDraw.exit(layout)

    @staticmethod
    def exit(layout: 'bpy.types.UILayout') -> 'bpy.types.UILayout.operator':
        """退出按钮"""
        from .ops.switch_ui import SwitchGestureWindow
        layout.alert = True
        return layout.operator(SwitchGestureWindow.bl_idname,
                               text='退出',
                               icon='PANEL_CLOSE'
                               )


class GesturePreferences(PublicProperty,
                         AddonPreferences,
                         PreferencesDraw):
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name='手势索引', update=lambda self, context: self.active_gesture.to_temp_kmi())

    draw_property: PointerProperty(type=DrawProperty)
    debug_property: PointerProperty(type=DebugProperty)
    other_property: PointerProperty(type=OtherProperty)
    gesture_property: PointerProperty(type=GestureProperty)
    add_element_property: PointerProperty(type=AddElementProperty)

    enabled: BoolProperty(
        name='启用手势',
        description="""启用禁用整个系统,主要是keymap""",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())
    show_page: EnumProperty(name='显示面板', items=[('GESTURE', 'Gesture', ''), ('PROPERTY', 'Property', '')])

    def get_gesture_data(self, get_all: bool = False) -> {}:
        from .ops.export_import import EXPORT_PROPERTY_ITEM, EXPORT_PROPERTY_EXCLUDE
        from .utils import PropertyGetUtils

        def filter_data(dd):
            res = {}
            if 'element_type' in dd:
                t = dd['element_type']
                for i in EXPORT_PROPERTY_ITEM[t]:
                    if i in dd:
                        res[i] = dd[i]
            else:
                res.update(dd)
            if 'element' in dd:
                res['element'] = {k: filter_data(v) for k, v in dd['element'].items()}
            return res

        data = {}
        for index, g in enumerate(self.pref.gesture):
            if g.selected or get_all:
                origin = PropertyGetUtils.props_data(g, EXPORT_PROPERTY_EXCLUDE)
                item = filter_data(origin)
                data[str(index)] = item
        return data

    @property
    def is_show_gesture(self):
        return self.show_page == 'GESTURE'

    @property
    def is_show_property(self):
        return self.show_page == 'PROPERTY'

    def draw(self, _):
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
