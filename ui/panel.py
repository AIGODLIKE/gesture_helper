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
        pref = self.pref
        row = self.layout.row(align=True)
        rr = row.row(align=True)
        rr.operator_context = "EXEC_DEFAULT"
        rr.prop(pref, 'enabled', text="", emboss=True)
        rr.operator("wm.save_userpref", text="", icon="FILE_TICK")

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


class GestureModalEventPanel(bpy.types.Panel, PublicProperty):
    bl_label = "Modal Event"
    bl_idname = "GESTURE_PT_Modal_Event"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GestureElementPanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        pref = get_pref()
        return pref.active_element and pref.active_event

    def draw(self, context):
        get_pref().active_element.draw_operator_modal(self.layout)


class GestureDebugPanel(bpy.types.Panel, PublicProperty):
    bl_label = "Debug"
    bl_idname = "GESTURE_PT_Debug"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.2
        PreferencesDraw.draw_ui_debug(layout)


panel_list = (
    GesturePanel,
    GestureItemPanel,
    GestureElementPanel,
    GesturePropertyPanel,
    GestureModalEventPanel,
    GestureDebugPanel,
)
register_classes, unregister_classes = bpy.utils.register_classes_factory(panel_list)


def register():
    pref = get_pref()
    for panel in panel_list:
        panel.bl_category = pref.draw_property.panel_name
    if pref.draw_property.panel_enable:
        register_classes()


def unregister():
    if GesturePanel.is_registered:
        unregister_classes()


def update_panel():
    unregister()
    register()
