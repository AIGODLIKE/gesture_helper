import bpy
from bpy.app.translations import pgettext
from bpy.props import EnumProperty, StringProperty

from ...utils.public import PublicOperator, PublicProperty, get_pref


class ElementProperty(PublicOperator, PublicProperty):
    def draw(self, context):
        layout = self.layout.column()
        layout.operator_context = "EXEC_DEFAULT"

        pointer = self.button_pointer
        prop = self.button_prop
        c = self.clipboard
        layout.context_pointer_set('button_pointer', pointer)
        layout.context_pointer_set('button_prop', prop)

        pref = get_pref()

        if prop:
            prop_type = prop.type

            text = pgettext(prop.name, prop.translation_context)
            type_translate = pgettext(prop_type, "*")
            relationship = pgettext(pref.add_element_property.relationship, "*")
            value = getattr(pointer, prop.identifier)

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
            layout.label(text=prop.identifier)
            layout.label(text=f"{type_translate} 类型")
            layout.label(text=f"添加属性到手势")
            layout.label(text=f"添加元素关系:{relationship}")
            layout.label(text=f"当前值:{value}")

            layout.label(text=f"button_pointer:\t{pointer}")
            layout.label(text=f"button_prop:\t{prop}")
            layout.label(text=f"clipboard:\t{self.clipboard}")

    def draw_boolean(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        for (i, n) in CreateElementProperty.boolean_mode.items:
            ops = layout.operator(CreateElementProperty.bl_idname, text=n)
            ops.boolean_mode = i

    def draw_int(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    def draw_float(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    def draw_string(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    def draw_enum(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        button_pointer = self.button_pointer
        button_prop = self.button_prop

        if button_prop.enum_items:
            items = button_prop.enum_items
        elif button_prop.enum_items_static:
            items = button_prop.enum_items_static
        elif button_prop.enum_items_static_ui:
            items = button_prop.enum_items_static_ui
        else:
            items = []

        if items:
            layout.prop(self, "enum_mode", text="枚举模式", expand=True)
            column = layout.column(align=True)
            for item in items:
                ops = column.operator(
                    CreateElementProperty.bl_idname,
                    text=f'{pgettext(item.name, "*")} ({item.identifier})',
                    icon=item.icon)
                ops.enum_mode = self.enum_mode
                ops.clipboard = self.clipboard

    def draw_pointer(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    def draw_collection(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...


class CreateElementProperty(ElementProperty):
    bl_label = '创建属性元素'
    bl_idname = 'gesture.create_element_property'

    boolean_mode: EnumProperty(
        items=[('SET_TRUE', '设置为 True', ''), ('SET_FALSE', '设置为 False', ''), ('SWITCH', '切换', '')],
        name='布尔模式',
        options={'HIDDEN', 'SKIP_SAVE'})
    enum_mode: EnumProperty(
        items=[('CYCLE', '循环设置 枚举值 (如果设置值和当前值相同,则切换到上一个值)',
                '使用 bpy.ops.wm.context_cycle_enum 操作符'),
               ('SET', '直接设置 枚举值', '使用 bpy.ops.wm.context_set_enum 操作符')],
        name='枚举模式',
        options={'HIDDEN', 'SKIP_SAVE'})
    clipboard: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def __init__(self):
        self.button_prop = None
        self.button_pointer = None

    @classmethod
    def poll(cls, context):
        button_pointer = getattr(bpy.context, "button_pointer", None)
        button_prop = getattr(bpy.context, "button_prop", None)
        return button_pointer and button_prop

    def draw(self, context):
        super().draw(context)

    def invoke(self, context, event):
        print("\ninvoke")
        self.copy_data_path()
        self.button_pointer = getattr(context, "button_pointer", None)
        self.button_prop = getattr(context, "button_prop", None)

        prop = {'operator': self, 'cancel_default': False, 'width': 300}
        return context.window_manager.invoke_props_dialog(**prop)

    def execute(self, _):
        print("\nexecute", self.clipboard)
        return {'FINISHED', "RUNNING_MODAL"}

    def copy_data_path(self):
        cp = bpy.ops.ui.copy_data_path_button
        if cp.poll():
            cp(full_path=True)
            self.clipboard = bpy.context.window_manager.clipboard
