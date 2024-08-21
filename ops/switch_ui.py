import bpy
from bpy.props import BoolProperty

from ..utils.public import PublicOperator


class SwitchGestureWindow(PublicOperator):
    bl_label = 'Popup gesture window'
    bl_idname = 'wm.popup_gesture_window'

    popup_window: BoolProperty(default=False, name='Popup window',
                               options={'SKIP_SAVE'})
    window_fullscreen_toggle: BoolProperty()

    def execute(self, context):
        if self.popup_window:
            bpy.ops.screen.userpref_show()
        from ..ui.replace_ui import SwitchGestureUi
        SwitchGestureUi.switch()
        self.show_header(context)
        context.preferences.active_section = 'ADDONS'
        if self.window_fullscreen_toggle:
            bpy.ops.screen.screen_full_area()
            bpy.ops.wm.window_fullscreen_toggle()
        bpy.ops.wm.redraw_timer(type='DRAW_WIN')
        return {'FINISHED'}

    @staticmethod
    def show_header(context: "bpy.types.Context"):
        def set_header(areas: list[bpy.types.Area]):
            for area in areas:
                if area.type == 'PREFERENCES':
                    area.spaces[0].show_region_header = True

        for win in context.window_manager.windows:
            set_header(win.screen.areas)
