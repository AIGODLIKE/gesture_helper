import bpy


class GESTURE_MT_add_element_menu(bpy.types.Menu):
    bl_label = "Add Element"

    def draw(self, context):
        from ..ops.qucik_add.create_switch_panel import CreateSwitchPanel
        layout = self.layout
        layout.label(text="Other")
        layout.operator(CreateSwitchPanel.bl_idname, text="Switch Panel")
