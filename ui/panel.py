import bpy

from ..utils.public import PublicProperty


class GesturePanel(bpy.types.Panel, PublicProperty):
    bl_label = "Gesture"
    bl_idname = "GESTURE_PT_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"

    def draw(self, context):
        self.pref.preferences_draw(self.layout)
