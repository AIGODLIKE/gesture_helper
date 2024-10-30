import bpy

from ..preferences.draw import PreferencesDraw
from ..preferences.draw_gesture import GestureDraw
from ..utils.public import PublicProperty, get_pref


class GesturePanel(bpy.types.Panel, PublicProperty):
    bl_label = "Gesture"
    bl_idname = "GESTURE_PT_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"

    def draw_header(self, context):
        from ..ops.qucik_add.gesture_preview import GesturePreview
        pref = self.pref
        row = self.layout.row(align=True)
        row.prop(pref, "enabled", icon_only=True)
        row.operator(GesturePreview.bl_idname, icon="RNA_ADD")

    def draw(self, context):
        ...


class GestureItemPanel(bpy.types.Panel, PublicProperty):
    bl_label = "Item"
    bl_idname = "GESTURE_PT_Item"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    def draw(self, context):
        layout = self.layout.row(align=True)
        layout.enabled = self.pref.enabled
        if not self.pref.active_gesture:
            GestureDraw.draw_gesture_cure(layout)
        GestureDraw.draw_gesture(layout)


class GestureElementPanel(bpy.types.Panel, PublicProperty):
    bl_label = "Element"
    bl_idname = "GESTURE_PT_Element"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    def draw(self, context):
        layout = self.layout
        layout.enabled = self.pref.enabled
        GestureDraw.draw_element(layout)


class GesturePropertyPanel(bpy.types.Panel, PublicProperty):
    bl_label = "Property"
    bl_idname = "GESTURE_PT_Property"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.2
        PreferencesDraw.draw_ui_property(layout)


panel_list = (GesturePanel, GestureItemPanel, GestureElementPanel, GesturePropertyPanel)
register_classes, unregister_classes = bpy.utils.register_classes_factory(panel_list)


def register():
    pref = get_pref()
    for panel in panel_list:
        panel.bl_category = pref.draw_property.panel_name
    register_classes()


def unregister():
    unregister_classes()


def update_panel():
    unregister()
    register()
