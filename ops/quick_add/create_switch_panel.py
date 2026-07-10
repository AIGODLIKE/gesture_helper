import bpy

from ...utils.panel import (
    get_panels_by_context,
    get_ui_panel_categories,
    get_ui_panels_by_space,
)
from ...utils.public import PublicProperty, poll_message_active_gesture
from ...utils.session_state import SessionState
from .switch_panel_category import GestureSwitchPanelCategory

# Prefer common editors first in the space-type enum.
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


def _ordered_space_types(by_space: dict) -> list[str]:
    ordered = [s for s in _SPACE_ORDER if s in by_space]
    ordered.extend(sorted(s for s in by_space if s not in _SPACE_ORDER))
    return ordered


def _refresh_space_cache(by_space: dict) -> list[str]:
    """Update session cache used by the dynamic EnumProperty. Returns ordered keys."""
    SessionState.switch_panel_by_space = dict(by_space)
    ordered = _ordered_space_types(by_space)
    if ordered:
        SessionState.switch_panel_enum_items = [(s, _space_label(s), '') for s in ordered]
    else:
        SessionState.switch_panel_enum_items = [('NONE', 'None', '')]
    return ordered


def _space_type_items(self, context):
    return SessionState.switch_panel_enum_items


class CreateSwitchPanel(bpy.types.Operator, PublicProperty):
    bl_label = 'Switch Panel Operator'
    bl_description = 'Create a gesture element that switches the N-panel tab in an editor'
    bl_options = {'REGISTER'}
    bl_idname = 'wm.gesture_create_switch_panel'

    panel_name: bpy.props.StringProperty()
    filter: bpy.props.StringProperty(options={"TEXTEDIT_UPDATE"}, name="Filter")
    space_type: bpy.props.EnumProperty(
        name="Editor",
        items=_space_type_items,
    )

    @classmethod
    def poll(cls, context):
        return poll_message_active_gesture(cls)

    def invoke(self, context, event):
        """source\\blender\\makesrna\\intern\\rna_screen.cc L348"""
        wm = context.window_manager

        by_space = get_ui_panels_by_space(context, check_poll=False)
        if not by_space:
            current = get_ui_panel_categories(context)
            if not current:
                current = get_panels_by_context(context, check_poll=False)
            by_space = {'VIEW_3D': current} if current else {}

        ordered = _refresh_space_cache(by_space)

        area_type = getattr(context.area, 'type', None)
        if 'VIEW_3D' in by_space:
            self.space_type = 'VIEW_3D'
        elif area_type in by_space:
            self.space_type = area_type
        elif ordered:
            self.space_type = ordered[0]

        return wm.invoke_props_dialog(**{'operator': self, 'width': 300})

    def execute(self, context):
        if self.panel_name == "":
            return {"FINISHED"}
        from ...element.element_cure import ElementCURE
        bpy.ops.wm.gesture_element_add(element_type="OPERATOR")
        last = ElementCURE.ADD.last_element
        last['operator_bl_idname'] = GestureSwitchPanelCategory.bl_idname
        props = {'panel_name': self.panel_name}
        if self.space_type and self.space_type != 'NONE':
            props['space_type'] = self.space_type
        last['operator_properties'] = str(props)
        last.name = self.panel_name
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "EXEC_DEFAULT"
        layout.prop(self, "space_type", text="")
        layout.prop(self, "filter")

        categories = SessionState.switch_panel_by_space.get(self.space_type, [])
        column = layout.column(align=True)
        for category in self._filtered_categories(categories):
            ops = column.operator(self.bl_idname, text=category)
            ops.panel_name = category
            ops.space_type = self.space_type

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
