import bpy

from ...utils.panel import get_panels_by_context, get_ui_panel_categories
from ...utils.public import PublicProperty, poll_message_active_gesture
from .switch_panel_category import GestureSwitchPanelCategory


class CreateSwitchPanel(bpy.types.Operator, PublicProperty):
    bl_label = 'Switch Panel Opterator'
    bl_idname = 'wm.gesture_create_switch_panel'

    panel_name: bpy.props.StringProperty()
    filter: bpy.props.StringProperty(options={"TEXTEDIT_UPDATE"}, name="Filter")
    panels = []

    @classmethod
    def poll(cls, context):
        return poll_message_active_gesture(cls)

    def invoke(self, context, event):
        """source\blender\makesrna\intern\rna_screen.cc L348"""
        wm = context.window_manager

        self.panels = get_ui_panel_categories(context)
        if not self.panels:
            self.panels = get_panels_by_context(context)
        return wm.invoke_props_dialog(**{'operator': self, 'width': 300})

    def execute(self, context):
        if self.panel_name == "":
            return {"FINISHED"}
        from ...element.element_cure import ElementCURE
        bpy.ops.wm.gesture_element_add(element_type="OPERATOR")
        last = ElementCURE.ADD.last_element
        last['operator_bl_idname'] = GestureSwitchPanelCategory.bl_idname
        last['operator_properties'] = str({'panel_name': self.panel_name})
        last.name = self.panel_name
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        # layout.label(text=context.area.type)
        # layout.label(text=context.region.type)
        layout.prop(self, "filter")
        column = layout.column(align=True)
        for category in self.panels:
            tn = bpy.app.translations.pgettext_iface(category).lower()
            if self.filter and (not self.filter.lower() in tn or not self.filter.lower() in category):
                continue
            column.operator(self.bl_idname, text=category).panel_name = category
