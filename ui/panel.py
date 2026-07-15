import bpy

from ..preferences.draw import PreferencesDraw
from ..preferences.draw_gesture import GestureDraw
from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.public import get_pref
from ..utils.rna_register import register_classes_safe, unregister_classes_safe


class GesturePanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Gesture"
    bl_idname = "GESTURE_PT_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"

    @classmethod
    def poll(cls, context):
        try:
            return get_pref().draw_property.panel_enable
        except (KeyError, AttributeError):
            return False

    def draw_header(self, context):
        pref = self.pref
        row = self.layout.row(align=True)
        rr = row.row(align=True)
        rr.operator_context = "EXEC_DEFAULT"
        rr.prop(pref, 'enabled', text="", emboss=True)
        rr.operator("wm.gesture_save_userpref", text="", icon="FILE_TICK")

    def draw(self, context):
        ...


class GestureItemPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Item"
    bl_idname = "GESTURE_PT_Item"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        layout = self.layout.row(align=True)
        layout.enabled = self.pref.enabled
        if not self.pref.active_gesture:
            GestureDraw.draw_gesture_cure(layout)
        GestureDraw.draw_gesture(layout)


class GestureElementPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Element"
    bl_idname = "GESTURE_PT_Element"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        # ElementUIList walks the same Element RNA the GPU overlay stores hit
        # boxes against; drawing it mid-modal can wipe those transient attrs.
        # Also skip during animation play (UI redraws every frame while playing).
        from ..utils.ui_draw_sync import heavy_panel_skip_message
        msg = heavy_panel_skip_message(context)
        if msg:
            self.layout.label(text=msg)
            return
        layout = self.layout
        layout.enabled = self.pref.enabled
        GestureDraw.draw_element(layout, include_modal=False)


class GestureModalEventPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Modal Event"
    bl_idname = "GESTURE_PT_Modal_Event"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    # bl_parent_id = GestureElementPanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if not GesturePanel.poll(context):
            return False
        pref = get_pref()
        active = pref.active_element
        if active is None or not active.operator_is_modal:
            return False
        return True

    def draw(self, context):
        from ..utils.ui_draw_sync import heavy_panel_skip_message
        msg = heavy_panel_skip_message(context)
        if msg:
            self.layout.label(text=msg)
            return
        get_pref().active_element.draw_operator_modal(self.layout)


class GesturePropertyPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Property"
    bl_idname = "GESTURE_PT_Property"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.2
        PreferencesDraw.draw_ui_property(layout)


panel_list = (
    GesturePanel,
    GestureItemPanel,
    GestureElementPanel,
    GestureModalEventPanel,
    GesturePropertyPanel,
)


def register():
    pref = get_pref()
    for panel in panel_list:
        panel.bl_category = pref.draw_property.panel_name
    if pref.draw_property.panel_enable:
        register_classes_safe(panel_list)


def unregister():
    unregister_classes_safe(panel_list)


def update_panel():
    unregister()
    register()
