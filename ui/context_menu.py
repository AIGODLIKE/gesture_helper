import bpy
from bpy.app.translations import pgettext

from ..ops.qucik_add.create_element_operator import CreateElementOperator
from ..ops.qucik_add.create_element_property import CreateElementProperty


class ContextMenu(bpy.types.Menu):
    bl_label = "Button Context Menu"
    show_context_menu = False  # 用于在添加后退出面板

    def draw(self, context):
        self.layout.separator()

    def draw_menu(self, menu, context):
        menu.context_menu(context)

    def context_menu(self, context):
        from ..src.translate import __name_translate__
        ContextMenu.show_context_menu = True
        show_operator = CreateElementOperator.poll(context)
        show_property = CreateElementProperty.poll(context)

        button_pointer = getattr(context, "button_pointer", None)

        show = not getattr(context, "show_gesture_add_menu", False)

        layout = self.layout

        if button_pointer and button_pointer.__class__.__name__ == "BlExtDummyGroup":
            layout.label(text="Add gesture", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")
            layout.label(text="Dynamic enumeration properties cannot be added!!")
        elif (show_operator or show_property) and show:
            button_prop = getattr(context, "button_prop", None)
            layout.context_pointer_set('show_gesture_add_menu', self)
            layout.label(text="Add gesture", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")

            if show_property:
                layout.operator(
                    CreateElementProperty.bl_idname,
                    text=pgettext("Add Property %s") % __name_translate__(button_prop.name)
                )

            if show_operator:
                button_operator = getattr(context, "button_operator", None)
                br = button_operator.bl_rna
                text = __name_translate__(br.name)
                row = layout.column(align=True)
                rr = row
                rr.operator_context = "EXEC_DEFAULT"
                rr.operator(CreateElementOperator.bl_idname, text=pgettext("Add Operator %s To Gesture") % text)
                rr = row
                rr.operator_context = "INVOKE_DEFAULT"
                rr.operator(CreateElementOperator.bl_idname, text="Modal Operator", icon="PRESET_NEW")


def register():
    if not hasattr(bpy.types, "WM_MT_button_context"):
        bpy.utils.register_class(type("WM_MT_button_context", (ContextMenu,), {}))
    bpy.types.WM_MT_button_context.append(ContextMenu.context_menu)


def unregister():
    bpy.types.WM_MT_button_context.remove(ContextMenu.context_menu)
