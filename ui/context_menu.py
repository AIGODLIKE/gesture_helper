import bpy
from bpy.app.translations import pgettext

from ..ops.qucik_add.create_element import CreateElement
from ..utils.public import get_pref


class PropertyMenu(bpy.types.Menu):
    bl_label = "Property Menu"
    bl_idname = "PROPERTY_MT_gesture_menu"

    def draw(self, context):
        button_pointer = getattr(bpy.context, "button_pointer", None)
        button_prop = getattr(bpy.context, "button_prop", None)
        button_operator = getattr(bpy.context, "button_operator", None)

        print(self.bl_idname, button_pointer, button_prop, button_operator)

        pref = get_pref()

        layout = self.layout

        prop_type = button_prop.type

        text = pgettext(button_prop.name, button_prop.translation_context)
        type_translate = pgettext(prop_type, "*")
        relationship = pgettext(pref.add_element_property.relationship, "*")
        value = getattr(button_pointer, button_prop.identifier)

        if prop_type == "BOOLEAN":
            self.draw_boolean(context, layout)
        elif prop_type == "INT":
            self.draw_int(context, layout)
        elif prop_type == "FLOAT":
            self.draw_float(context, layout)
        elif prop_type == "STRING":
            self.draw_string(context, layout)
        elif prop_type == "ENUM":
            self.draw_enum(context, layout)
        elif prop_type == "POINTER":
            self.draw_pointer(context, layout)
        elif prop_type == "COLLECTION":
            self.draw_collection(context, layout)

        layout.separator()
        layout.label(text=text)
        layout.label(text=button_prop.identifier)
        layout.label(text=f"{type_translate} 类型")
        layout.label(text=f"添加属性到手势")
        layout.label(text=f"添加元素关系:{relationship}")
        layout.label(text=f"当前值:{value}")

    @staticmethod
    def draw_boolean(context: bpy.types.Context, layout: bpy.types.UILayout):
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
    def draw_int(context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    @staticmethod
    def draw_float(context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    @staticmethod
    def draw_string(context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    @staticmethod
    def draw_enum(context: bpy.types.Context, layout: bpy.types.UILayout):
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        button_operator = getattr(context, "button_operator", None)

        if button_prop.enum_items:
            items = button_prop.enum_items
        elif button_prop.enum_items_static:
            items = button_prop.enum_items_static
        elif button_prop.enum_items_static_ui:
            items = button_prop.enum_items_static_ui
        else:
            items = []

        if items:
            layout.label(text="循环")
            for item in items:
                ops = layout.operator(
                    CreateElement.bl_idname,
                    text=f'{pgettext(item.name, "*")} ({item.identifier})',
                    icon=item.icon)
                ops.mode = "PROPERTY"
                ops.enum_mode = "CYCLE"
            layout.separator()
            layout.label(text="设置")
            for item in items:
                ops = layout.operator(
                    CreateElement.bl_idname,
                    text=f'{pgettext(item.name, "*")} ({item.identifier})',
                    icon=item.icon)
                ops.mode = "PROPERTY"
                ops.enum_mode = "SET"

            layout.label(text=f"button_pointer:\t{button_pointer}")
            layout.label(text=f"button_prop:\t{button_prop}")
            layout.label(text=f"button_operator:\t{button_operator}")

    @staticmethod
    def draw_pointer(context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    @staticmethod
    def draw_collection(context: bpy.types.Context, layout: bpy.types.UILayout):
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
            layout.label(text="添加手势", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")

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
