import bpy

from .draw_gesture import GestureDraw
from ..utils.public import get_pref


class PreferencesDraw(GestureDraw):

    @staticmethod
    def preferences_draw(layout: bpy.types.UILayout):
        """绘制偏好设置
        """
        pref = get_pref()
        column = layout.column(align=True)

        PreferencesDraw.draw_topbar(column)

        sub_column = column.column(align=True)
        if pref.is_show_gesture:
            sub_column.enabled = pref.enabled

        getattr(pref, f'draw_ui_{pref.show_page.lower()}')(sub_column)
        # draw_ui_property
        # draw_ui_gesture

    @staticmethod
    def draw_topbar(layout: 'bpy.types.UILayout'):
        """绘制顶部栏"""
        from ..ops.qucik_add.gesture_preview import GesturePreview
        pref = get_pref()
        row = layout.row(align=True)
        row.prop(pref, 'enabled', text="")

        row.prop(pref, 'show_page', expand=True)
        row.operator(GesturePreview.bl_idname, icon="RNA_ADD", text=pref.__ts__(GesturePreview.bl_label))

    @staticmethod
    def draw_ui_property(layout):
        """
        桧制属性部分
        :param layout:
        :return:
        """
        from .. import preferences
        pref = get_pref()

        row = layout.row()
        row.use_property_split = True
        column = row.column(align=True)
        column.prop(pref.draw_property, "panel_name")
        preferences.BackupsProperty.draw_backups(column)
        preferences.DebugProperty.draw_debug(column)

        col = row.box().column(align=True)
        col.label(text='手势')
        preferences.GestureProperty.draw_gesture_property(col)
        preferences.DrawProperty.draw_text_property(col)
        preferences.DrawProperty.draw_color_property(col)

    @staticmethod
    def exit(layout: 'bpy.types.UILayout') -> 'bpy.types.UILayout.operator':
        """退出按钮"""
        layout.alert = True
        from ..ops.switch_ui import SwitchGestureWindow
        return layout.operator(SwitchGestureWindow.bl_idname,
                               text='退出',
                               icon='PANEL_CLOSE'
                               )
