__panel__ = []
__menu__ = []

import bpy
from bpy.props import EnumProperty, StringProperty

from ...src.translate import __name_translate__
from ...utils.public import PublicOperator, PublicProperty, get_pref


class CreatePanelMenu(PublicOperator, PublicProperty):
    bl_label = 'Create Panel Menu'
    bl_idname = 'gesture.create_panel_menu'

    type: EnumProperty(items=[("PANEL", "Panel", ""), ("MENU", "Menu", "")])
    create_id_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return get_pref().active_gesture is not None

    def execute(self, context):
        t = getattr(bpy.types, self.create_id_name, None)
        if t is None:
            return {"CANCELLED"}

        pref = get_pref()
        bpy.ops.gesture.element_add(
            add_active_radio=True,
            element_type="OPERATOR",
            relationship=pref.add_element_property.relationship,
        )
        ae = self.active_element
        if self.type == "PANEL":
            ae.operator_bl_idname = f'bpy.ops.wm.call_panel(name="{self.create_id_name}")'
        elif self.type == "MENU":
            ae.operator_bl_idname = f'bpy.ops.wm.call_menu(name="{self.create_id_name}")'
        else:
            return {"CANCELLED"}
        ae.name = t.bl_label if t.bl_label else getattr(t, "bl_idname", self.create_id_name)
        return {"FINISHED"}


def draw_add(self, context):
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
    text = f"{__name_translate__('Add')} {__name_translate__(self.bl_label)} {__name_translate__(t)}({self.bl_idname})"
    ops = layout.operator(CreatePanelMenu.bl_idname, text=text)
    ops.type = t.upper()
    ops.create_id_name = self.bl_idname


def register():
    for p in bpy.types.Panel.__subclasses__():
        if hasattr(p, "draw"):
            p.append(draw_add)
            __panel__.append(p)
    for m in bpy.types.Menu.__subclasses__():
        if hasattr(m, "draw"):
            m.append(draw_add)
            __menu__.append(m)


def unregister():
    for p in __panel__:
        p.remove(draw_add)
    for m in __menu__:
        m.remove(draw_add)
