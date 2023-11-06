import bpy.utils
from bpy.props import CollectionProperty, IntProperty, BoolProperty
from bpy.types import AddonPreferences

from . import gesture
from .public import ADDON_NAME, get_pref, PublicProperty


class GestureDraw:

    @staticmethod
    def draw_gesture_cure(layout: bpy.types.UILayout):
        GestureDraw.public_cure(layout, gesture.GestureCURE)

    @staticmethod
    def draw_gesture_key(layout):
        pref = get_pref()
        active = pref.active_gesture
        if active:
            active.draw_key(layout)
        else:
            layout.label(text='Not Select Gesture')

    @staticmethod
    def draw_gesture_list(layout: bpy.types.UILayout):
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
    def draw_element_list(layout: bpy.types.UILayout):
        from ..ui.ui_list import ElementUIList
        pref = get_pref()
        ges = pref.active_gesture
        if ges:
            row = layout.row(align=True)
            GestureDraw.draw_element_cure(row)
            row.template_list(
                ElementUIList.bl_idname,
                ElementUIList.bl_idname,
                ges,
                'element',
                ges,
                'index_element',
            )
        else:
            layout.label(text='请添加或选择一个手势')

    @staticmethod
    def draw_element_cure(layout: bpy.types.UILayout):
        from .gesture.element import ElementCURE
        GestureDraw.public_cure(layout, ElementCURE)

    @staticmethod
    def public_cure(layout, cls):
        pref = get_pref()

        column = layout.column(align=True)
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
        if cls.__class__.__name__ == 'ElementCURE':
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
        layout = self.layout
        layout.label(text='right_layout')

        column = layout.column()
        column.prop(self, 'enable')
        split = column.split()
        GestureDraw.draw_gesture_list(split)
        GestureDraw.draw_element_list(split)

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


class GesturePreferences(
    AddonPreferences,
    PublicProperty,
    BlenderPreferencesDraw,
):
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=gesture.Gesture)
    index_gesture: IntProperty(name='手势索引')

    enable: BoolProperty(
        name='启用手势',
        description="""启用禁用整个系统,主要是keymap""",
        default=True, update=lambda: gesture.GestureKey.key_restart())

    is_move_element: BoolProperty(
        default=False,
        description="""TODO 移动元素 整个元素需要只有移动操作符可用"""  # TODO
    )

    def draw(self, context):
        from ..ops.switch_ui import SwitchGestureWindow

        layout = self.layout
        layout.operator(SwitchGestureWindow.bl_idname)


def register():
    gesture.register()
    bpy.utils.register_class(GesturePreferences)


def unregister():
    gesture.unregister()
    bpy.utils.unregister_class(GesturePreferences)
