import bpy

from ...utils.panel import get_panels_by_context
from ...utils.public import PublicProperty


class CreateSwitchPanel(bpy.types.Operator, PublicProperty):
    bl_label = 'Create Switch Panel'
    bl_idname = 'gesture.create_switch_panel'

    panel_name: bpy.props.StringProperty()
    filter: bpy.props.StringProperty(options={"TEXTEDIT_UPDATE"}, name="Filter")

    def invoke(self, context, event):
        """source\blender\makesrna\intern\rna_screen.cc L348"""
        wm = context.window_manager
        return wm.invoke_props_dialog(**{'operator': self, 'width': 300})

    def execute(self, context):
        from ...element.element_cure import ElementCURE
        bpy.ops.gesture.element_add(element_type="OPERATOR")
        last = ElementCURE.ADD.last_element
        last.operator_bl_idname = f'bpy.ops.wm.context_set_string(data_path="area.regions[5].active_panel_category", value="{self.panel_name}")'
        last.name = self.panel_name
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        # layout.label(text=context.area.type)
        # layout.label(text=context.region.type)
        layout.prop(self, "filter")
        column = layout.column(align=True)
        for category in get_panels_by_context(context, region="UI"):
            tn = bpy.app.translations.pgettext_iface(category).lower()
            if self.filter and (not self.filter.lower() in tn or not self.filter.lower() in category):
                continue
            column.operator(self.bl_idname, text=category).panel_name = category
