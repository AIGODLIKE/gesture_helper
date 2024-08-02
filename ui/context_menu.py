import bpy
from bpy.app.translations import pgettext

from ..ops.qucik_add.create_element_operator import CreateElementOperator
from ..ops.qucik_add.create_element_property import CreateElementProperty


class ContextMenu:
    bl_label = "Button Context Menu"

    def draw(self, context):
        self.layout.separator()

    def draw_menu(self, menu, context):
        menu.context_menu(context)

    def context_menu(self, context):
        show_operator = CreateElementOperator.poll(context)
        show_property = CreateElementProperty.poll(context)

        button_pointer = getattr(context, "button_pointer", None)

        show = not getattr(context, "show_gesture_add_menu", False)

        layout = self.layout

        if button_pointer and button_pointer.__class__.__name__ == "BlExtDummyGroup":
            layout.label(text="添加手势", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")
            layout.label(text="动态枚举属性无法添加!!")
        elif (show_operator or show_property) and show:
            button_prop = getattr(context, "button_prop", None)
            layout.context_pointer_set('show_gesture_add_menu', self)
            layout.label(text="添加手势", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")

            if show_property:
                layout.operator(CreateElementProperty.bl_idname,
                                text=f"添加属性 {pgettext(button_prop.name, '*')}")

            if show_operator:
                button_operator = getattr(context, "button_operator", None)
                br = button_operator.bl_rna
                text = pgettext(br.name, br.translation_context)
                layout.operator(CreateElementOperator.bl_idname, text=f'添加操作符 {text} 到手势')


def register():
    if not hasattr(bpy.types, "WM_MT_button_context"):
        tp = type(
            "WM_MT_button_context",
            (ContextMenu, bpy.types.Menu), {})
        bpy.utils.register_class(tp)
    bpy.types.WM_MT_button_context.append(ContextMenu.context_menu)


def unregister():
    bpy.types.WM_MT_button_context.remove(ContextMenu.context_menu)
