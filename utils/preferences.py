import bpy.utils
from bpy.props import CollectionProperty, IntProperty, BoolProperty, PointerProperty, FloatProperty
from bpy.types import AddonPreferences, PropertyGroup

from . import gesture
from .gesture.element.element_property import ElementAddProperty
from .public import ADDON_NAME, get_pref, PublicProperty

AddElementProperty = type('Add Element Property', (ElementAddProperty, PropertyGroup), {})


class DrawProperty(PropertyGroup):
    element_split_factor: FloatProperty(name='拆分系数', default=0.06, max=1, min=0.001)
    element_split_space: IntProperty(name='拆分空间', default=1000, min=500, max=100000)


class ElementDraw:
    @staticmethod
    def draw_property(layout: 'bpy.types.UILayout') -> None:
        pref = get_pref()
        act = pref.active_element
        if act:
            act.draw_ui_property(layout)
        else:
            layout.label(text='请 选择或添加 一个手势元素')

    @staticmethod
    def draw_element_add_remove(layout: 'bpy.types.UILayout', cls) -> None:
        column = layout.column()
        column.scale_x = 0.5
        add = get_pref().add_element_property

        column.row().prop(add, 'relationship', expand=True, )
        column.row().prop(add, 'element_type', expand=True, )
        if not add.is_element:
            column.row().prop(add, 'selected_type', expand=True, )

        ops = column.operator(
            cls.ADD.bl_idname,
            icon='ADD',
            text=''
        )
        ops.relationship = add.relationship
        ops.element_type = add.element_type
        ops.selected_type = add.selected_type

        column.operator(
            cls.REMOVE.bl_idname,
            icon='REMOVE',
            text=''
        )


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
    def draw_gesture(layout: bpy.types.UILayout) -> None:
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
        GestureDraw.draw_gesture_key(column)

    @staticmethod
    def draw_element(layout: bpy.types.UILayout) -> None:
        from ..ui.ui_list import ElementUIList
        pref = get_pref()
        ges = pref.active_gesture
        if ges:
            row = layout.row(align=True)
            GestureDraw.draw_element_cure(row)

            column = row.column()
            column.template_list(
                ElementUIList.bl_idname,
                ElementUIList.bl_idname,
                ges,
                'element',
                ges,
                'index_element',
            )
            ElementDraw.draw_property(column)
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
        column = layout.column(align=True)
        if is_element:
            ElementDraw.draw_element_add_remove(layout, cls)
        else:
            column.operator(
                cls.ADD.bl_idname,
                icon='ADD',
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
            column.operator(
                cls.MOVE.bl_idname,
                icon='CANCEL' if pref.is_move_element else 'GRIP',  # TODO if is move
                text=''
            )
        column.operator(
            cls.SORT.bl_idname,
            icon='SORT_ASC',
            text=''
        ).is_next = True


class BlenderPreferencesDraw(GestureDraw):

    # 绘制右边层
    def right_layout(self: bpy.types.Panel, context: bpy.context):
        pref = get_pref()
        layout = self.layout
        layout.label(text='right_layout')

        column = layout.column()
        column.prop(pref, 'enabled')
        split = column.split()
        GestureDraw.draw_gesture(split)
        GestureDraw.draw_element(split)

    def left_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='left_layout')

    def bottom_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='bottom_layout')
        BlenderPreferencesDraw.exit(layout)

    def left_bottom_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='left_bottom_layout')
        BlenderPreferencesDraw.exit(layout)

    @staticmethod
    def exit(layout: 'bpy.types.UILayout') -> 'bpy.types.UILayout.operator':
        """退出按钮"""
        from ..ops.switch_ui import SwitchGestureWindow
        layout.alert = True
        return layout.operator(SwitchGestureWindow.bl_idname,
                               text='退出',
                               icon='PANEL_CLOSE'
                               )


class GesturePreferences(PublicProperty,
                         AddonPreferences,
                         BlenderPreferencesDraw):
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name='手势索引')
    is_preview: BoolProperty(name='是在预览模式')  # TODO

    add_element_property: PointerProperty(type=AddElementProperty)
    draw_property: PointerProperty(type=DrawProperty)

    enabled: BoolProperty(
        name='启用手势',
        description="""启用禁用整个系统,主要是keymap""",
        default=True, update=lambda self, context: gesture.GestureKeymap.key_restart())

    is_move_element: BoolProperty(
        default=False,
        description="""TODO 移动元素 整个元素需要只有移动操作符可用"""  # TODO
    )

    def draw(self, context):
        from ..ops.switch_ui import SwitchGestureWindow

        layout = self.layout
        layout.operator(SwitchGestureWindow.bl_idname)
        self.right_layout(layout)


classes_list = (
    DrawProperty,
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
