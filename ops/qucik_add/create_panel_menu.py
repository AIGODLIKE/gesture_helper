__panel__ = []
__menu__ = []

import bpy
from bpy.props import EnumProperty, StringProperty

from ...utils.public import PublicOperator, PublicProperty, get_pref


class CreatePanelMenu(PublicOperator, PublicProperty):
    bl_label = 'Create Panel Menu'
    bl_idname = 'gesture.create_panel_menu'

    type: EnumProperty(items=[("PANEL", "Panel", ""), ("MENU", "Menu", "")])
    create_id_name: StringProperty()
    is_draw = False

    @classmethod
    def poll(cls, context):
        return get_pref().active_gesture is not None

    def execute(self, context):
        t = getattr(bpy.types, self.create_id_name, None)
        if t is None:
            return {"CANCELLED"}

        pref = get_pref()
        self.cache_clear()
        with pref.add_element_property.active_radio():
            bpy.ops.gesture.element_add(element_type="OPERATOR")
            ae = self.active_element
            if self.type == "PANEL":
                ae.operator_bl_idname = f'bpy.ops.wm.call_panel(name="{self.create_id_name}")'
            elif self.type == "MENU":
                ae.operator_bl_idname = f'bpy.ops.wm.call_menu(name="{self.create_id_name}")'
            else:
                return {"CANCELLED"}
            ae.name = t.bl_label if t.bl_label else getattr(t, "bl_idname", self.create_id_name)
            return {"FINISHED"}

    def invoke(self, context, event):
        if self.__class__.is_draw:
            unregister()
        else:
            register()

        for area in context.screen.areas:
            area.tag_redraw()
        self.__class__.is_draw = not self.__class__.is_draw
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
    rr.operator(CreatePanelMenu.bl_idname, text="",icon="PANEL_CLOSE")


exclude_panel = ["PROPERTIES_PT_navigation_bar"]


def register():
    for p in bpy.types.Panel.__subclasses__():
        if hasattr(p, "draw") and "gesture" not in p.__name__.lower() and p.__name__ not in exclude_panel:
            p.append(draw_add)
            __panel__.append(p)
    for m in bpy.types.Menu.__subclasses__():
        if hasattr(m, "draw") and "gesture" not in m.__name__.lower() and m.__name__ not in exclude_panel:
            m.append(draw_add)
            __menu__.append(m)


def unregister():
    for p in __panel__:
        p.remove(draw_add)
    for m in __menu__:
        m.remove(draw_add)
