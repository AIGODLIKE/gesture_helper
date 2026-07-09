import bpy

from ...utils.panel import get_ui_region


class GestureSwitchPanelCategory(bpy.types.Operator):
    """Switch N-panel tab in the current area (any editor)."""

    bl_idname = 'wm.gesture_switch_panel_category'
    bl_label = 'Switch N Panel Category'
    bl_options = {'INTERNAL'}

    panel_name: bpy.props.StringProperty(name='Panel Name')
    # Empty = any editor with an N-panel; default VIEW_3D for gesture usage in 3D View.
    space_type: bpy.props.StringProperty(name='Space Type', default='VIEW_3D')

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
        if self.space_type and area.type != self.space_type:
            return {'CANCELLED'}
        ui_region, _ = get_ui_region(area)
        if ui_region is None:
            return {'CANCELLED'}
        try:
            ui_region.active_panel_category = self.panel_name
        except (TypeError, AttributeError, RuntimeError, ValueError):
            return {'CANCELLED'}
        return {'FINISHED'}
