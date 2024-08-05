import bpy
from bl_ui.properties_paint_common import UnifiedPaintPanel
from bpy.app.translations import pgettext
from bpy.props import EnumProperty, StringProperty

from ...utils.property_data import CREATE_ELEMENT_DATA_PATHS, CREATE_ELEMENT_BRUSH_PATH
from ...utils.public import get_pref, PublicOperator, PublicProperty


class OpsProperty:
    boolean_mode: EnumProperty(
        items=[('SET_TRUE', '设置为 True', ''), ('SET_FALSE', '设置为 False', ''), ('SWITCH', '切换', '')],
        name='布尔模式',
        options={'HIDDEN'})
    enum_mode: EnumProperty(
        items=[('CYCLE', '循环设置 枚举值 (如果设置值和当前值相同,则切换到上一个值)',
                '使用 bpy.ops.wm.context_cycle_enum 操作符'),
               ('SET', '直接设置 枚举值', '使用 bpy.ops.wm.context_set_enum 操作符')],
        name='枚举模式',
        options={'HIDDEN'})
    data_path: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    property_type: EnumProperty(items=[
        ("BOOLEAN", "Boolean", ""),
        ("INT", " Integer", ""),
        ("FLOAT", "Float", ""),
        ("STRING", " String", ""),
        ("ENUM", "Enumeration", ""),
        ("POINTER", " Pointer", ""),
        ("COLLECTION", "Collection", ""),
    ])


class Draw(PublicOperator, PublicProperty, OpsProperty):
    def draw(self, context):
        from ...ui.context_menu import ContextMenu

        layout = self.layout.column()
        layout.operator_context = "EXEC_DEFAULT"

        pointer = self.button_pointer
        prop = self.button_prop
        layout.context_pointer_set('button_pointer', pointer)
        layout.context_pointer_set('button_prop', prop)
        layout.context_pointer_set('show_gesture_add_menu', self)

        pref = get_pref()

        if prop and ContextMenu.show_context_menu:
            prop_type = prop.type

            text = pgettext(prop.name, prop.translation_context)
            type_translate = pgettext(prop_type, "*")
            relationship = pgettext(pref.add_element_property.relationship, "*")
            value = getattr(pointer, prop.identifier)

            if self.data_path != "":
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
            else:
                layout.alert = True
                layout.label(text="无法获取数据路径")
                layout.label(text="无法添加")

            layout.separator()
            layout.label(text=text)
            layout.label(text=prop.identifier)
            layout.label(text=f"{type_translate} 类型")
            layout.label(text=f"添加属性到手势")
            layout.label(text=f"添加元素关系:{relationship}")
            layout.label(text=f"当前值:{value}")

            layout.label(text=f"button_pointer:\t{pointer}")
            layout.label(text=f"button_prop:\t{prop}")
            layout.label(text=f"subtype:\t{prop.subtype}")
            layout.label(text=f"data_path:\t{self.data_path}")

    def draw_boolean(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        for item in self.rna_type.properties["boolean_mode"].enum_items:  # 绘制添加的布尔模式
            ops = layout.operator(CreateElementProperty.bl_idname, text=item.name)
            ops.boolean_mode = item.identifier
            ops.data_path = self.data_path
            ops.property_type = "BOOLEAN"

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
                ops.data_path = self.data_path

    def draw_pointer(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...

    def draw_collection(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        ...


class Create(Draw):
    def create_bool(self):
        """
        bpy.ops.wm.context_set_boolean()
        bpy.ops.wm.context_toggle()
        :return:
        """
        bpy.ops.gesture.element_add(add_active_radio=True, element_type="OPERATOR")
        ae = self.active_element
        if ae:
            bm = self.boolean_mode
            # if bm == "SET_TRUE":
            #
            # elif bm == "SET_FALSE":
            #     ...
            # elif bm == "SWITCH":

    def create_int(self):
        ...

    def create_float(self):
        ...

    def create_string(self):
        ...

    def create_enum(self):
        ...

    def create(self):
        """
        https://docs.blender.org/api/master/bpy_types_enum_items/property_type_items.html#property-type-items
        TODO

        BOOLEAN:Boolean.
        INT:Integer.
        FLOAT:Float.
        STRING:String.
        ENUM:Enumeration.
        POINTER:Pointer.
        COLLECTION:Collection.

        :return:
        """
        pt = self.property_type
        if pt == "BOOLEAN":
            self.create_boolean()
        elif pt == "INT":
            self.create_int()
        elif pt == "FLOAT":
            self.create_float()
        elif pt == "STRING":
            self.create_string()
        elif pt == "ENUM":
            self.create_enum()


class CreateElementProperty(Create):
    bl_label = '创建属性元素'
    bl_idname = 'gesture.create_element_property'

    # bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.button_prop = None
        self.button_pointer = None

    @classmethod
    def poll(cls, context) -> bool:
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        return button_pointer and button_prop

    def invoke(self, context, event) -> set[str]:
        print(f"\n{self.bl_idname}\tinvoke")
        self.from_context_get_info(context)
        self.copy_data_path()

        return context.window_manager.invoke_popup(**{'operator': self, 'width': 600})

    def execute(self, context) -> set[str]:
        from ...ui.context_menu import ContextMenu
        ContextMenu.show_context_menu = False

        self.from_context_get_info(context)
        name = self.button_pointer.__class__.__name__
        identifier = self.button_prop.identifier

        print("\nexecute", self.data_path)
        return {'FINISHED', "RUNNING_MODAL"}

    def copy_data_path(self) -> None:
        """复制数据路径"""
        pointer_name = self.button_pointer.__class__.__name__
        prop_identifier = self.button_prop.identifier
        id_data_type = type(self.button_pointer.id_data)
        if id_data_type is bpy.types.Mesh:
            self.data_path = f"bpy.context.object.data.{prop_identifier}"
            return
        elif id_data_type is bpy.types.Text and bpy.context.area.ui_type == "TEXT_EDITOR":  # 是文本编辑器
            self.data_path = f"bpy.context.space_data.text.{prop_identifier}"
            return
        elif pointer_name == "View3DShading" and bpy.context.area.ui_type == "PROPERTIES":  # 工作台渲染
            self.data_path = f"bpy.context.scene.display.shading.{prop_identifier}"
            return
        elif pointer_name in CREATE_ELEMENT_DATA_PATHS:
            self.data_path = f"{CREATE_ELEMENT_DATA_PATHS[pointer_name]}.{prop_identifier}"
            return
        elif pointer_name == 'Brush' and bpy.context.object:
            mode = UnifiedPaintPanel.get_brush_mode(bpy.context)
            if mode in CREATE_ELEMENT_BRUSH_PATH:
                self.data_path = f"{CREATE_ELEMENT_BRUSH_PATH[mode]}.{prop_identifier}"
                return

        # 使用Blender操作符
        cp = bpy.ops.ui.copy_data_path_button
        if cp.poll():
            cp(full_path=True)
            clipboard = bpy.context.window_manager.clipboard
            print("use clipboard", clipboard)
            self.data_path = clipboard

    def from_context_get_info(self, context) -> None:
        """从上下文获取信息"""
        self.button_pointer = getattr(context, "button_pointer", None)
        self.button_prop = getattr(context, "button_prop", None)
