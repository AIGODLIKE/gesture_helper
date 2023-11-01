import bpy.utils
from bpy.props import CollectionProperty, IntProperty, BoolProperty
from bpy.types import AddonPreferences

from .gesture import Gesture
from .public import ADDON_NAME
from . import gesture


class BlenderPreferencesDraw:

    # 绘制右边层
    def right_layout(self: bpy.types.Panel, context: bpy.context):
        layout = self.layout
        layout.label(text='right_layout')

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


class GesturePreferences(AddonPreferences):
    bl_idname = ADDON_NAME

    # 项配置
    gesture: CollectionProperty(type=Gesture)
    gesture_index: IntProperty(name='手势索引')


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
