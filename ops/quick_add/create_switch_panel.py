import bpy

from ...utils.panel import (
    get_panels_by_context,
    get_ui_panel_categories,
    get_ui_panels_by_space,
)
from ...utils.public import PublicProperty, poll_message_active_gesture
from .switch_panel_category import GestureSwitchPanelCategory

# Prefer common editors first when listing N-panel tabs from Preferences.
_SPACE_ORDER = (
    'VIEW_3D',
    'IMAGE_EDITOR',
    'NODE_EDITOR',
    'SEQUENCE_EDITOR',
    'CLIP_EDITOR',
    'DOPESHEET_EDITOR',
    'GRAPH_EDITOR',
    'NLA_EDITOR',
    'TEXT_EDITOR',
    'SPREADSHEET',
)


def _space_label(space_type: str) -> str:
    try:
        enum_items = bpy.types.Area.bl_rna.properties['type'].enum_items
        item = enum_items.get(space_type)
        if item is not None:
            return item.name
    except (AttributeError, KeyError, TypeError):
        pass
    return space_type


class CreateSwitchPanel(bpy.types.Operator, PublicProperty):
    bl_label = 'Switch Panel Opterator'
    bl_idname = 'wm.gesture_create_switch_panel'

    panel_name: bpy.props.StringProperty()
    filter: bpy.props.StringProperty(options={"TEXTEDIT_UPDATE"}, name="Filter")
    # list[tuple[space_type, list[str]]] grouped by editor, or flat list[str] fallback
    panels = []

    @classmethod
    def poll(cls, context):
        return poll_message_active_gesture(cls)

    def invoke(self, context, event):
        """source\\blender\\makesrna\\intern\\rna_screen.cc L348"""
        wm = context.window_manager

        # Always list N-panel tabs for every editor (VIEW_3D, UV, Node, …).
        # Creating from Preferences / 3D N-panel must not hide other editors.
        by_space = get_ui_panels_by_space(context, check_poll=False)
        if by_space:
            ordered = [s for s in _SPACE_ORDER if s in by_space]
            ordered.extend(sorted(s for s in by_space if s not in _SPACE_ORDER))
            self.panels = [(space, by_space[space]) for space in ordered]
        else:
            current = get_ui_panel_categories(context)
            self.panels = current or get_panels_by_context(context, check_poll=False)
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
        layout.prop(self, "filter")
        column = layout.column(align=True)

        if self.panels and isinstance(self.panels[0], tuple):
            for space_type, categories in self.panels:
                filtered = self._filtered_categories(categories)
                if not filtered:
                    continue
                box = column.box()
                box.label(text=_space_label(space_type))
                self._draw_category_buttons(box.column(align=True), filtered)
        else:
            self._draw_category_buttons(column, self._filtered_categories(self.panels))

    def _filtered_categories(self, categories):
        fl = self.filter.lower()
        if not fl:
            return list(categories)
        result = []
        for category in categories:
            tn = bpy.app.translations.pgettext_iface(category).lower()
            if fl in tn or fl in category.lower():
                result.append(category)
        return result

    def _draw_category_buttons(self, column, categories):
        for category in categories:
            column.operator(self.bl_idname, text=category).panel_name = category
