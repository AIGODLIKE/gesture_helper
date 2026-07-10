__panel__ = []
__menu__ = []

import bpy
from bpy.props import EnumProperty, StringProperty

from ...utils.panel import iter_menu_classes, iter_panel_classes
from ...utils.public import PublicOperator, PublicProperty, get_pref, poll_message_active_gesture
from ...utils.session_state import SessionState


class CreatePanelMenu(PublicOperator, PublicProperty):
    bl_label = 'Create Panel Menu'
    bl_idname = 'wm.gesture_create_panel_menu'
    bl_description = 'Inject a quick-add button into Blender panels and menus'
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
        if SessionState.panel_menu_injecting:
            unregister()
        else:
            register()

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


def register():
    unregister()
    for p in iter_panel_classes():
        if hasattr(p, "draw") and "gesture" not in p.__name__.lower() and p.__name__ not in exclude_panel:
            p.append(draw_add)
            __panel__.append(p)
    for m in iter_menu_classes():
        if hasattr(m, "draw") and "gesture" not in m.__name__.lower() and m.__name__ not in exclude_panel:
            m.append(draw_add)
            __menu__.append(m)
    SessionState.panel_menu_injecting = True


def unregister():
    for p in __panel__:
        try:
            p.remove(draw_add)
        except (ValueError, RuntimeError, AttributeError):
            pass
    for m in __menu__:
        try:
            m.remove(draw_add)
        except (ValueError, RuntimeError, AttributeError):
            pass
    __panel__.clear()
    __menu__.clear()
    SessionState.panel_menu_injecting = False
