# Replace preferences UI draw
import bpy

from ..preferences import PreferencesDraw


class ReplaceUI:

    # Draw right-side layer
    def right_layout(self: bpy.types.Panel, _):
        PreferencesDraw.preferences_draw(self.layout)

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


class SwitchGestureUi:
    """Configure UI override."""
    ui_draw_func = {
        'left': None,
        'right': None,
        'bottom': None,
        'left_button': None,
        'is_overwrite': False,  # UI draw was replaced
    }

    @classmethod
    def switch(cls):
        """Toggle between original and custom UI."""
        is_overwrite = cls.ui_draw_func['is_overwrite']
        if is_overwrite:
            cls.reduction_ui()
        else:
            cls.overwrite_ui()
        cls.refresh_layout()

    @classmethod
    def refresh_layout(cls):
        """Redraw all areas."""
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP')

    @classmethod
    def overwrite_ui(cls):
        """Override UI draw function."""
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
        """Set active layout draw method."""
        bpy.types.USERPREF_PT_addons.draw = ReplaceUI.right_layout
        bpy.types.USERPREF_PT_navigation_bar.draw = ReplaceUI.left_layout
        bpy.types.USERPREF_HT_header.draw = ReplaceUI.bottom_layout
        bpy.types.USERPREF_PT_save_preferences.draw = ReplaceUI.left_bottom_layout

    @classmethod
    def reduction_ui(cls):
        """Restore original UI draw."""
        data = cls.ui_draw_func
        if data['is_overwrite']:
            data['is_overwrite'] = False
            bpy.types.USERPREF_PT_navigation_bar.draw = data['left']
            bpy.types.USERPREF_PT_addons.draw = data['right']
            bpy.types.USERPREF_HT_header.draw = data['bottom']
            bpy.types.USERPREF_PT_save_preferences.draw = data['left_button']
