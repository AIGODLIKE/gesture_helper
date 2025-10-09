import bpy


class GESTURE_MT_add_element_menu(bpy.types.Menu):
    bl_label = "Add Element"

    def draw(self, context):
        from ..ops.qucik_add.create_switch_panel import CreateSwitchPanel
        from ..ops.qucik_add.create_panel_menu import CreatePanelMenu
        layout = self.layout
        layout.label(text="Other")
        layout.operator(CreateSwitchPanel.bl_idname, text="Switch N Panel")
        text = "Cancel adding panel or menu" if CreatePanelMenu.is_draw else "Call Panel or Menu"
        layout.operator(CreatePanelMenu.bl_idname, text=text)
