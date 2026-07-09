import bpy

from ...utils.panel import get_ui_region


class GestureSwitchPanelCategory(bpy.types.Operator):
    """Switch N-panel tab in the current area (any editor)."""

    bl_idname = 'wm.gesture_switch_panel_category'
    bl_label = 'Switch N Panel Category'
    bl_options = {'INTERNAL'}

    panel_name: bpy.props.StringProperty(name='Panel Name')

    @classmethod
    def poll(cls, context):
        area = context.area
        if area is None:
            return False
        ui_region, _ = get_ui_region(area)
        return ui_region is not None

    def execute(self, context):
        area = context.area
        if area is None or not self.panel_name:
            return {'CANCELLED'}
        ui_region, _ = get_ui_region(area)
        if ui_region is None:
            return {'CANCELLED'}
        ui_region.active_panel_category = self.panel_name
        return {'FINISHED'}
