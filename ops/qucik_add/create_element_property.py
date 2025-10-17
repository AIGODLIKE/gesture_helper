import bpy
from bl_ui.properties_paint_common import UnifiedPaintPanel
from bpy.app.translations import pgettext, pgettext_n
from bpy.props import EnumProperty, StringProperty, IntProperty, FloatProperty, BoolProperty

from ...utils.enum import CREATE_ELEMENT_VALUE_MODE_ENUM
from ...utils.property_data import CREATE_ELEMENT_DATA_PATHS, CREATE_ELEMENT_BRUSH_PATH
from ...utils.public import get_pref, PublicOperator, PublicProperty


class Enum:
    enum_mode: EnumProperty(
        items=[
            ('SET', 'Direct setting of enumeration values', 'Use bpy.ops.wm.context_set_enum operator'),
            ('CYCLE',
             'Cyclic setting of the enumeration value (if the set value is the same as the current value, the enumeration switches to the previous value)',
             'Use bpy.ops.wm.context_cycle_enum operator'),
            ('TOGGLE', 'Toggle setting Enumeration values (toggle between two enumeration values)',
             'Use bpy.ops.wm.context_toggle_enum operator'),
            ('MENU', 'Menu', 'Using the menu display enumeration with the bpy.ops.wm.context_menu_enum operator'),
            ('PIE', 'Pie Menu',
             'Using the bpy.ops.wm.context_pie_enum operator Use the pie menu to display the enumeration (up to 8 items)'),
        ],
        name='枚举模式',
        options={'HIDDEN', 'SKIP_SAVE'})

    ___enum___ = []  # 防止脏数据

    def __get_enum__(self, context):
        """获取枚举"""
        button_prop = getattr(CreateElementProperty, "button_prop",
                              getattr(context, "button_prop",
                                      getattr(self, "button_prop", None)
                                      )
                              )
        if button_prop:
            if button_prop.enum_items:
                items = button_prop.enum_items
            elif button_prop.enum_items_static:
                items = button_prop.enum_items_static
            elif button_prop.enum_items_static_ui:
                items = button_prop.enum_items_static_ui
            else:
                items = []
        else:
            items = []
        it = [(item.identifier, item.name, item.description, item.icon, index)
              for (index, item) in enumerate(items)]
        if it:
            if it != OpsProperty.___enum___:
                OpsProperty.___enum___ = it
        else:
            if OpsProperty.___enum___ != CREATE_ELEMENT_VALUE_MODE_ENUM:
                OpsProperty.___enum___ = CREATE_ELEMENT_VALUE_MODE_ENUM
        return OpsProperty.___enum___

    enum_value_a: EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_value_b: EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_reverse: BoolProperty(default=False, name="Invert", description="Reverse enumeration order on loop")
    enum_wrap: BoolProperty(default=True, name="Cycle",
                            description="Automatically jumps if it is the last or first value in the loop")


class OpsProperty(Enum):
    boolean_mode: EnumProperty(
        items=[('SET_TRUE', 'Set to True', ''), ('SET_FALSE', 'Set to False', ''), ('SWITCH', 'Switch', '')],
        name='Boolean Mode',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    data_path: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    property_type: EnumProperty(items=[
        ("BOOLEAN", "Boolean", ""),
        ("INT", " Integer", ""),
        ("FLOAT", "Float", ""),
        ("STRING", " String", ""),
        ("ENUM", "Enumeration", ""),
        # ("POINTER", " Pointer", ""),
        # ("COLLECTION", "Collection", ""),
    ])

    value_mode: EnumProperty(items=CREATE_ELEMENT_VALUE_MODE_ENUM, name="Value Mode")
    int_value: IntProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="Int Value", default=0)
    float_value: FloatProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="Float Value", default=0)
    string_value: StringProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="String Value")

    @property
    def __data_path__(self) -> str:
        """bpy.context.space_data.show_gizmo -> space_data.show_gizmo"""
        return self.data_path.replace("bpy.context.", "")

    @classmethod
    def clear_info(cls):
        """清理信息"""
        cls.button_pointer = None
        cls.button_prop = None

    @classmethod
    def from_context_get_info(cls, context) -> None:
        """从上下文获取信息"""
        cls.button_pointer = getattr(context, "button_pointer", None)
        cls.button_prop = getattr(context, "button_prop", None)


class Draw(PublicOperator, PublicProperty, OpsProperty):
    def draw(self, context):
        from ...ui.context_menu import ContextMenu

        layout = self.layout.column()
        layout.operator_context = "EXEC_DEFAULT"

        self.update_data(layout, context)

        pref = get_pref()

        pointer = self.button_pointer
        prop = self.button_prop
        if prop and ContextMenu.show_context_menu:
            prop_type = prop.type

            value = getattr(pointer, prop.identifier)

            if self.data_path != "":
                if prop_type == "BOOLEAN":
                    self.draw_boolean(context, layout)
                elif prop_type == "INT":
                    self.draw_int(context, layout)
                elif prop_type == "FLOAT":
                    if prop.is_array:
                        layout.label(text="Array property not supported")
                    else:
                        self.draw_float(context, layout)
                elif prop_type == "STRING":
                    self.draw_string(context, layout)
                elif prop_type == "ENUM":
                    self.draw_enum(context, layout)
            else:
                layout.alert = True
                layout.label(text="Unable to get data path")
                layout.label(text="Unable to add")

            if self.debug_property.debug_mode:
                text = pgettext(prop.name, prop.translation_context)
                type_translate = pgettext(prop_type, "*")
                relationship = pgettext(pref.add_element_property.relationship, "*")
                layout.separator()
                layout.label(text=text)
                layout.label(text=prop.identifier)
                layout.label(text=str(type_translate))
                layout.label(text="Adding Property to Gestures")
                layout.label(text=pgettext("Add element relationship: %s") % relationship)
                layout.label(text=pgettext("Current value: %s") % value)

                layout.label(text=f"button_pointer:\t{pointer}")
                layout.label(text=f"button_prop:\t{prop}")
                layout.label(text=f"a:\t{getattr(context, 'button_prop', None)}")
                layout.label(text=f"subtype:\t{prop.subtype}")
                layout.label(text=f"data_path:\t{self.data_path}")

    def draw_boolean(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        layout.label(text="Set Boolean Value")
        for item in self.rna_type.properties["boolean_mode"].enum_items:  # 绘制添加的布尔模式
            ops = layout.operator(CreateElementProperty.bl_idname, text=item.name)
            ops.boolean_mode = item.identifier
            ops.data_path = self.data_path
            ops.property_type = "BOOLEAN"

    def draw_int(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        layout.label(text="Modify Int Value")
        layout.prop(self, "value_mode", expand=True)
        layout.separator()
        if self.value_mode == "SET_VALUE":
            layout.prop(self, "int_value")
        layout.separator()
        ops = layout.operator(CreateElementProperty.bl_idname, text="Add")
        ops.value_mode = self.value_mode
        ops.data_path = self.data_path
        ops.int_value = self.int_value
        ops.property_type = "INT"

    def draw_float(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        layout.label(text="Modify float value")
        layout.prop(self, "value_mode", expand=True)
        layout.separator()
        if self.value_mode == "SET_VALUE":
            layout.prop(self, "float_value")
        layout.separator()
        ops = layout.operator(CreateElementProperty.bl_idname, text="Add")
        ops.value_mode = self.value_mode
        ops.data_path = self.data_path
        ops.float_value = self.float_value
        ops.property_type = "FLOAT"

    def draw_string(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        layout.label(text="Modify String")
        layout.separator()
        layout.prop(self, "string_value")
        layout.separator()
        ops = layout.operator(CreateElementProperty.bl_idname, text="Add")
        ops.data_path = self.data_path
        ops.string_value = self.string_value
        ops.property_type = "STRING"

    def draw_enum(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        layout.label(text="Modify Enumeration")

        layout.separator()

        layout.prop(self, "enum_mode", text="Enumeration Value", expand=True)
        if self.enum_mode == "TOGGLE":
            row = layout.row(align=True)
            a = row.column(align=True)
            a.label(text="Value A")
            a.prop(self, "enum_value_a", expand=True)

            b = row.column(align=True)
            b.label(text="Value B")
            b.prop(self, "enum_value_b", expand=True)
        elif self.enum_mode == "SET":
            layout.prop(self, "enum_value_a", expand=True)

        if self.enum_mode == "CYCLE":
            layout.separator()
            layout.prop(self, "enum_reverse")
            layout.prop(self, "enum_wrap")

        layout.separator()

        cc = layout.column(align=True)
        is_eq = self.enum_mode == "TOGGLE" and self.enum_value_a == self.enum_value_b
        if is_eq:
            cc.alert = True
            cc.label(text="Value A == Value B")
            cc = cc.column(align=True)
            cc.enabled = False

        ops = cc.operator(CreateElementProperty.bl_idname, text="Add")
        ops.data_path = self.data_path
        ops.enum_mode = self.enum_mode
        ops.enum_value_a = self.enum_value_a
        ops.enum_value_b = self.enum_value_b
        ops.enum_reverse = self.enum_reverse
        ops.enum_wrap = self.enum_wrap
        ops.property_type = "ENUM"


class Create(Draw):
    def create_boolean(self):
        """
        bpy.ops.wm.context_set_boolean()
        bpy.ops.wm.context_toggle()
        :return:
        """
        ae = self.active_element
        if ae:
            bm = self.boolean_mode
            if bm == "SET_TRUE":
                ae.operator_bl_idname = f"wm.context_set_boolean(data_path='{self.__data_path__}', value=True)"
            elif bm == "SET_FALSE":
                ae.operator_bl_idname = f"wm.context_set_boolean(data_path='{self.__data_path__}', value=False)"
            elif bm == "SWITCH":
                ae.operator_bl_idname = f"wm.context_toggle(data_path='{self.__data_path__}')"

    def create_int(self):
        ae = self.active_element
        from ..modal_mouse import ModalMouseOperator
        if ae:
            vm = self.value_mode
            if vm == "SET_VALUE":
                ae.operator_bl_idname = f"wm.context_set_int(data_path='{self.__data_path__}', value={self.int_value})"
            else:
                bl = f"{ModalMouseOperator.bl_idname}(data_path='{self.__data_path__}', value_mode='{self.value_mode}')"
                ae.operator_bl_idname = bl

    def create_float(self):
        ae = self.active_element
        from ..modal_mouse import ModalMouseOperator
        if ae:
            vm = self.value_mode
            if vm == "SET_VALUE":
                ae.operator_bl_idname = f"wm.context_set_float(data_path='{self.__data_path__}', value={self.float_value})"
            else:
                bl = f"{ModalMouseOperator.bl_idname}(data_path='{self.__data_path__}', value_mode='{self.value_mode}')"
                ae.operator_bl_idname = bl

    def create_string(self):
        """
        bpy.ops.wm.context_set_string()
        :return:
        """
        ae = self.active_element
        if ae:
            bi = f"wm.context_set_string(data_path='{self.__data_path__}', value='{self.string_value}')"
            ae.operator_bl_idname = bi

    def create_enum(self):
        """
        bpy.ops.wm.context_set_enum(data_path="", value="")
        bpy.ops.wm.context_cycle_enum(data_path="", reverse=False, wrap=False)
        bpy.ops.wm.context_toggle_enum(data_path="", value_1="", value_2="")
        bpy.ops.wm.context_menu_enum(data_path="")
        bpy.ops.wm.context_pie_enum(data_path="")
        :return:
        """
        ae = self.active_element
        if ae:
            em = self.enum_mode
            if em == "SET":
                ae.operator_bl_idname = f"wm.context_set_enum(data_path='{self.__data_path__}', value='{self.enum_value_a}')"
            elif em == "CYCLE":
                ae.operator_bl_idname = f"wm.context_cycle_enum(data_path='{self.__data_path__}', reverse={self.enum_reverse},wrap={self.enum_wrap})"
            elif em == "TOGGLE":
                ae.operator_bl_idname = f"wm.context_toggle_enum(data_path='{self.__data_path__}', value_1='{self.enum_value_a}', value_2='{self.enum_value_b}')"
            elif em == "MENU":
                ae.operator_bl_idname = f"wm.context_menu_enum(data_path='{self.__data_path__}')"
            elif em == "PIE":
                ae.operator_bl_idname = f"wm.context_pie_enum(data_path='{self.__data_path__}')"

    def create(self):
        """
        https://docs.blender.org/api/master/bpy_types_enum_items/property_type_items.html#property-type-items

        BOOLEAN:Boolean.
        INT:Integer.
        FLOAT:Float.
        STRING:String.
        ENUM:Enumeration.
        POINTER:Pointer.
        COLLECTION:Collection.
        :return:
        """
        pref = get_pref()
        with pref.add_element_property.active_radio():
            bpy.ops.gesture.element_add(element_type="OPERATOR")
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

            ae = self.active_element
            if ae and self.button_prop:
                ae.name = self.__prop_name__

    @property
    def __prop_name__(self) -> str:
        """属性名称"""
        bp = self.button_prop
        if bp.type == "ENUM":
            if self.enum_mode == "SET":
                value = self.enum_value_a
                for item in bp.enum_items:
                    if item.identifier == value:
                        return pgettext_n(item.name, bp.translation_context)
        return pgettext_n(bp.name, bp.translation_context)


class CreateElementProperty(Create):
    bl_label = 'Create Property Element'
    bl_idname = 'gesture.create_element_property'

    button_pointer = None
    button_prop = None

    @classmethod
    def poll(cls, context) -> bool:
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        return button_pointer and button_prop

    def invoke(self, context, event) -> set[str]:
        self.from_context_get_info(context)
        self.copy_data_path()
        self.init_string()
        return context.window_manager.invoke_popup(**{'operator': self, 'width': 400})

    def execute(self, context) -> set[str]:
        self.clear_info()
        from ...ui.context_menu import ContextMenu
        ContextMenu.show_context_menu = False

        self.from_context_get_info(context)
        name = self.button_pointer.__class__.__name__
        identifier = self.button_prop.identifier

        print("\nexecute", self.data_path, name, identifier, )
        self.create()
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

    def init_string(self):
        prop = self.button_prop
        if prop.type == "STRING":
            self.string_value = getattr(self.button_pointer, prop.identifier, "")

    def update_data(self, layout, context):
        """更新数据"""
        pointer = self.button_pointer
        if pointer:
            layout.context_pointer_set('button_pointer', pointer)
        else:
            po = getattr(context, "button_pointer", None)
            if po:
                self.button_pointer = po

        prop = self.button_prop
        if prop:
            layout.context_pointer_set('button_prop', prop)
        else:
            pr = getattr(context, "button_prop", None)
            if pr:
                self.button_prop = pr

        layout.context_pointer_set('show_gesture_add_menu', self)
