import bpy

from ..utils.icons import ui_icon


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


class GESTURE_MT_layout_preset_menu(bpy.types.Menu):
    bl_label = 'Layout Presets'

    def draw(self, context):
        from ..element.element_cure import ElementCURE

        layout = self.layout
        for identifier, text, icon in (
            ('PANEL', 'Panel Column', 'MENU_PANEL'),
            ('TOOLBAR', 'Toolbar Row', 'ALIGN_JUSTIFY'),
            ('SPLIT', 'Two Columns', 'SPLIT_HORIZONTAL'),
        ):
            operator = layout.operator(
                ElementCURE.AddLayoutPreset.bl_idname,
                text=text,
                icon=ui_icon(icon),
            )
            operator.preset = identifier


class GESTURE_MT_main_action_menu(bpy.types.Menu):
    bl_label = 'Gesture Action'

    def draw(self, context):
        container = getattr(context, 'gesture_main_action_layout', None)
        if container is None:
            return
        layout = self.layout
        effective = container.main_element
        for item in container.panel_leaf_items:
            if not (item.is_operator or item.is_property_display):
                continue
            layout.prop(
                item,
                'main_item',
                text=item.name_translate,
                icon=ui_icon(
                    'RADIOBUT_ON' if item == effective else 'RADIOBUT_OFF'
                ),
                toggle=True,
            )
