import bpy


class GESTURE_MT_add_element_menu(bpy.types.Menu):
    bl_label = "Other Elements"

    def draw(self, context):
        from ..ops.quick_add.create_switch_panel import CreateSwitchPanel
        from ..ops.quick_add.create_panel_menu import CreatePanelMenu
        from ..utils.session_state import SessionState
        layout = self.layout
        layout.label(text="Other")
        layout.operator(CreateSwitchPanel.bl_idname, text="Switch N-Panel Tab")
        text = (
            "Cancel adding panel or menu"
            if SessionState.panel_menu_adding
            else "Adding Panel or Menu"
        )
        layout.operator(CreatePanelMenu.bl_idname, text=text)
