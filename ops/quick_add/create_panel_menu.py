__panel__ = []
__menu__ = []

import bpy
from bpy.props import EnumProperty, StringProperty

from ...utils.panel import iter_menu_classes, iter_panel_classes
from ...utils.public import PublicOperator, get_pref, poll_message_active_gesture
from ...utils.structure_cache_ops import StructureCacheOps
from ...utils.session_state import SessionState


class CreatePanelMenu(PublicOperator, StructureCacheOps):
    bl_label = 'Create Panel Menu'
    bl_idname = 'wm.gesture_create_panel_menu'
    bl_description = 'Show a quick-add button on Blender panels and menus'
    bl_options = {'REGISTER'}

    type: EnumProperty(items=[("PANEL", "Panel", ""), ("MENU", "Menu", "")])
    create_id_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return poll_message_active_gesture(cls)

    def execute(self, context):
        from ...element.element_cure import ElementCURE

        t = getattr(bpy.types, self.create_id_name, None)
        if t is None:
            return {"CANCELLED"}

        pref = get_pref()
        with pref.add_element_property.active_radio():
            result = bpy.ops.wm.gesture_element_add(element_type="OPERATOR")
            if 'CANCELLED' in result:
                return {"CANCELLED"}
            ae = ElementCURE.ADD.last_element

        if ae is None:
            self.report({'ERROR'}, "Failed to add gesture element")
            return {"CANCELLED"}

        if self.type == "PANEL":
            ae.operator_bl_idname = f'bpy.ops.wm.call_panel(name="{self.create_id_name}")'
        elif self.type == "MENU":
            ae.operator_bl_idname = f'bpy.ops.wm.call_menu(name="{self.create_id_name}")'
        else:
            return {"CANCELLED"}
        ae.name = t.bl_label if t.bl_label else getattr(t, "bl_idname", self.create_id_name)
        self.cache_clear()
        return {"FINISHED"}

    def invoke(self, context, event):
        if SessionState.panel_menu_adding:
            stop_adding()
        else:
            start_adding()

        for area in context.screen.areas:
            area.tag_redraw()
        return {"FINISHED"}


def draw_add(self, context):
    from bpy.app.translations import pgettext_iface
    t = "unknown"
    layout = self.layout
    if bpy.types.Menu in self.__class__.__bases__:
        layout = self.layout.row(align=True)
        t = "Menu"
    elif bpy.types.Panel in self.__class__.__bases__:
        layout = self.layout.column(align=True)
        t = "Panel"

    layout.separator()
    layout.alert = True
    row = layout.row(align=True)
    row.operator_context = "EXEC_DEFAULT"
    text = f"{pgettext_iface('Adding')} {pgettext_iface(self.bl_label)} {pgettext_iface(t)}({self.bl_idname})"
    ops = row.operator(CreatePanelMenu.bl_idname, text=text)
    ops.type = t.upper()
    ops.create_id_name = self.bl_idname
    rr = row.row(align=True)
    rr.operator_context = "INVOKE_DEFAULT"
    rr.operator(CreatePanelMenu.bl_idname, text="", icon="PANEL_CLOSE")


exclude_panel = ["PROPERTIES_PT_navigation_bar"]


def _can_append(cls) -> bool:
    return (
        hasattr(cls, "draw")
        and "gesture" not in cls.__name__.lower()
        and cls.__name__ not in exclude_panel
    )


def _safe_remove_draw(cls) -> None:
    try:
        cls.remove(draw_add)
    except (ValueError, RuntimeError, AttributeError, TypeError):
        pass


def start_adding():
    """Append quick-add buttons to panels/menus.

    Only call this when the user explicitly starts "Adding Panel or Menu".
    Do not run from add-on enable or gesture preview.
    """
    # Always clear first so cancel / re-enter never stacks duplicate draw hooks.
    stop_adding()
    for p in iter_panel_classes():
        if _can_append(p):
            p.append(draw_add)
            __panel__.append(p)
    for m in iter_menu_classes():
        if _can_append(m):
            m.append(draw_add)
            __menu__.append(m)
    SessionState.panel_menu_adding = True


def stop_adding():
    """Remove quick-add draw hooks from panels/menus.

    Called when the user cancels adding, and from add-on ``unregister()`` so
    disable/uninstall never leaves draw_add on Blender UI classes.
    """
    for p in __panel__:
        _safe_remove_draw(p)
    for m in __menu__:
        _safe_remove_draw(m)
    # Full sweep: tracked lists can be lost after script reload / partial fail.
    for p in iter_panel_classes():
        if _can_append(p):
            _safe_remove_draw(p)
    for m in iter_menu_classes():
        if _can_append(m):
            _safe_remove_draw(m)
    __panel__.clear()
    __menu__.clear()
    SessionState.panel_menu_adding = False
