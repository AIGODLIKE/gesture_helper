import bpy

from ..utils.public import PublicProperty


class GesturePanel(bpy.types.Panel, PublicProperty):
    bl_label = "Gesture"
    bl_idname = "GESTURE_PT_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"

    def draw(self, context):
        from ..ops.qucik_add.gesture_preview import GesturePreview
        if GesturePreview.is_preview_mode:
            from ..preferences.draw_gesture import GestureDraw
            GestureDraw.draw_element(self.layout)
        else:
            self.pref.preferences_draw(self.layout)
