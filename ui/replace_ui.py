# 替换偏好设置ui
import bpy


class SwitchGestureUi:
    """设置UI"""
    ui_draw_func = {
        'left': None,
        'right': None,
        'bottom': None,
        'left_button': None,
        'is_overwrite': False,  # 是被替换了的
    }

    @classmethod
    def switch(cls):
        """切换两种状态"""
        is_overwrite = cls.ui_draw_func['is_overwrite']
        if is_overwrite:
            cls.reduction_ui()
        else:
            cls.overwrite_ui()
        cls.refresh_layout()

    @classmethod
    def refresh_layout(cls):
        """刷新界面"""
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP')

    @classmethod
    def overwrite_ui(cls):
        """重写ui"""
        data = cls.ui_draw_func
        if not data['is_overwrite']:
            data['is_overwrite'] = True
            data['left'] = bpy.types.USERPREF_PT_navigation_bar.draw
            data['right'] = bpy.types.USERPREF_PT_addons.draw
            data['bottom'] = bpy.types.USERPREF_HT_header.draw
            data['left_button'] = bpy.types.USERPREF_PT_save_preferences.draw
            cls.set_layout_func()

    @classmethod
    def set_layout_func(cls):
        """设置活动Layout的绘制方法"""
        from ..utils.preferences import BlenderPreferencesDraw
        bpy.types.USERPREF_PT_addons.draw = BlenderPreferencesDraw.right_layout
        bpy.types.USERPREF_PT_navigation_bar.draw = BlenderPreferencesDraw.left_layout
        bpy.types.USERPREF_HT_header.draw = BlenderPreferencesDraw.bottom_layout
        bpy.types.USERPREF_PT_save_preferences.draw = BlenderPreferencesDraw.left_bottom_layout

    @classmethod
    def reduction_ui(cls):
        """还原ui"""
        data = cls.ui_draw_func
        if data['is_overwrite']:
            data['is_overwrite'] = False
            bpy.types.USERPREF_PT_navigation_bar.draw = data['left']
            bpy.types.USERPREF_PT_addons.draw = data['right']
            bpy.types.USERPREF_HT_header.draw = data['bottom']
            bpy.types.USERPREF_PT_save_preferences.draw = data['left_button']
