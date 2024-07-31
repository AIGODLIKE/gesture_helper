import bpy
from bpy.app.translations import pgettext

from ..ops.qucik_add.create_element import CreateElement
from ..utils.public import get_pref


class PropertyMenu(bpy.types.Menu):
    bl_label = "Property Menu"
    bl_idname = "PROPERTY_MT_gesture_menu"

    def draw(self, context):
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        pref = get_pref()

        layout = self.layout

        bt = button_prop.type

        text = pgettext(button_prop.name, button_prop.translation_context)
        type_translate = pgettext(bt, "*")
        r = pgettext(pref.add_element_property.relationship, "*")
        value = getattr(button_pointer, button_prop.identifier)

        if bt == "BOOLEAN":
            self.draw_boolean(layout)
        elif bt == "INT":
            self.draw_int(layout)
        elif bt == "FLOAT":
            self.draw_float(layout)
        elif bt == "STRING":
            self.draw_string(layout)
        elif bt == "ENUM":
            self.draw_enum(layout)
        elif bt == "POINTER":
            self.draw_pointer(layout)
        elif bt == "COLLECTION":
            self.draw_collection(layout)

        layout.separator()
        layout.label(text=text)
        layout.label(text=button_prop.identifier)
        layout.label(text=f"{type_translate} 类型")
        layout.label(text=f"添加属性到手势")
        layout.label(text=f"添加元素关系:{r}")
        layout.label(text=f"当前值:{value}")

    @staticmethod
    def draw_boolean(layout):
        ops = layout.operator(CreateElement.bl_idname, text='设置为 True')
        ops.mode = "PROPERTY"
        ops.boolean_mode = "SET_TRUE"
        ops = layout.operator(CreateElement.bl_idname, text='设置为 False')
        ops.mode = "PROPERTY"
        ops.boolean_mode = "SET_FALSE"
        ops = layout.operator(CreateElement.bl_idname, text='切换值')
        ops.mode = "PROPERTY"
        ops.boolean_mode = "SWITCH"

    @staticmethod
    def draw_int(layout):
        ...

    @staticmethod
    def draw_float(layout):
        ...

    @staticmethod
    def draw_string(layout):
        ...

    @staticmethod
    def draw_enum(layout):
        ...

    @staticmethod
    def draw_pointer(layout):
        ...

    @staticmethod
    def draw_collection(layout):
        ...


class ContextMenu:
    bl_label = "Button Context Menu"

    def draw(self, context):
        self.layout.separator()

    def draw_menu(self, menu, context):
        menu.context_menu(context)

    def context_menu(self, context):

        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        button_operator = getattr(context, "button_operator", None)

        if button_pointer is not None or button_prop is not None or button_operator is not None:
            layout = self.layout
            layout.alert = True
            layout.label(text="添加手势", icon="GEOMETRY_SET")

            if button_pointer is not None or button_prop is not None:
                layout.menu(PropertyMenu.bl_idname, text="添加属性")
            if button_operator is not None:
                br = button_operator.bl_rna
                text = pgettext(br.name, br.translation_context)
                ops = layout.operator(CreateElement.bl_idname, text=f'添加操作符 {text} 到手势')
                ops.mode = "OPERATOR"

            layout.label(text=f"button_pointer:\t{button_pointer}")
            layout.label(text=f"button_prop:\t{button_prop}")
            layout.label(text=f"button_operator:\t{button_operator}")


def register():
    if not hasattr(bpy.types, "WM_MT_button_context"):
        tp = type(
            "WM_MT_button_context",
            (ContextMenu, bpy.types.Menu), {})
        bpy.utils.register_class(tp)
    bpy.utils.register_class(PropertyMenu)
    bpy.types.WM_MT_button_context.append(ContextMenu.context_menu)


def unregister():
    bpy.types.WM_MT_button_context.remove(ContextMenu.context_menu)
    bpy.utils.unregister_class(PropertyMenu)
