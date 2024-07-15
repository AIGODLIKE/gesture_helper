import bpy

from .draw_gesture import GestureDraw
from ..utils.public import get_pref


class PreferencesDraw(GestureDraw):

    @staticmethod
    def preferences_draw(layout: bpy.types.UILayout):
        """绘制偏好设置"""
        from ..ops.gesture_quick_add import GestureQuickAdd
        pref = get_pref()

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(pref, 'enabled', text='')
        row.prop(pref, 'show_page', expand=True)
        row.operator(GestureQuickAdd.bl_idname, icon="RNA_ADD")
        sub_column = column.column(align=True)
        if pref.is_show_gesture:
            sub_column.enabled = pref.enabled
        getattr(pref, f'draw_ui_{pref.show_page.lower()}')(sub_column)

    @staticmethod
    def draw_ui_property(layout):
        """
        桧制属性部分
        :param layout:
        :return:
        """
        from ..preferences.other import OtherProperty
        from ..preferences import DrawProperty, DebugProperty
        from . import GestureProperty

        row = layout.row()
        row.use_property_split = True
        column = row.column(align=True)

        OtherProperty.draw_backups(column)

        DebugProperty.draw_debug(column)

        col = row.column(align=True)
        col.label(text='手势')
        GestureProperty.draw_gesture_property(col)
        DrawProperty.draw_text_property(col)
        DrawProperty.draw_color_property(col)

    @staticmethod
    def exit(layout: 'bpy.types.UILayout') -> 'bpy.types.UILayout.operator':
        """退出按钮"""
        layout.alert = True
        from ..ops.switch_ui import SwitchGestureWindow
        return layout.operator(SwitchGestureWindow.bl_idname,
                               text='退出',
                               icon='PANEL_CLOSE'
                               )
