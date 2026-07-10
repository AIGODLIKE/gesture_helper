import bpy
from bl_ui.properties_paint_common import UnifiedPaintPanel
from bpy.app.translations import pgettext, pgettext_n
from bpy.props import EnumProperty, StringProperty, IntProperty, FloatProperty, BoolProperty

from ...utils.enum import ENUM_NUMBER_VALUE_CHANGE_MODE, from_rna_get_enum_items, ENUM_BOOL_VALUE_CHANGE_MODE
from ...utils.property_data import (
    CREATE_ELEMENT_DATA_PATHS,
    CREATE_ELEMENT_BRUSH_PATH,
    convert_data_path_to_context,
    normalize_context_data_path,
    resolve_context_data_path,
    resolve_id_data_context_path,
    resolve_view_layer_data_path,
)
from ...utils.public import get_pref, PublicOperator, PublicProperty, debug_print


class Enum:
    _enum_items_cache: list = []
    _enum_items_prop_id: int | None = None

    _ENUM_MODE_DRAW_ITEMS = (
        ('SET', 'Direct setting of enumeration values'),
        ('CYCLE', 'Cyclic setting of the enumeration value'),
        ('TOGGLE', 'Toggle setting Enumeration values'),
        ('MENU', 'Menu'),
        ('PIE', 'Pie Menu'),
    )

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
        name='Enum mode',
        options={'HIDDEN', 'SKIP_SAVE'})

    ___enum___ = []  # legacy alias kept for compatibility
    _EMPTY_ENUM_ITEMS = [('NONE', '(No items)', '')]

    def __get_enum__(self, context):
        """Get enum items for the right-clicked RNA property."""
        button_prop = (
            getattr(context, "button_prop", None)
            or getattr(CreateElementProperty, "button_prop", None)
        )
        prop_id = id(button_prop) if button_prop is not None else None
        if prop_id != Enum._enum_items_prop_id:
            Enum._enum_items_prop_id = prop_id
            items = from_rna_get_enum_items(button_prop)
            Enum._enum_items_cache = items if items else []
            Enum.___enum___ = Enum._enum_items_cache
        if Enum._enum_items_cache:
            return Enum._enum_items_cache
        # Never fall back to number-mode items; that pollutes enum_value_a/b.
        return Enum._EMPTY_ENUM_ITEMS

    @property
    def has_enum_items(self) -> bool:
        return bool(Enum._enum_items_cache)

    enum_value_a: EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_value_b: EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_reverse: BoolProperty(default=False, name="Invert", description="Reverse enumeration order on loop")
    enum_wrap: BoolProperty(default=True, name="Cycle",
                            description="Automatically jumps if it is the last or first value in the loop")


class OpsProperty(Enum):
    boolean_mode: EnumProperty(
        items=ENUM_BOOL_VALUE_CHANGE_MODE,
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

    value_mode: EnumProperty(items=ENUM_NUMBER_VALUE_CHANGE_MODE, name="Value Mode")
    int_value: IntProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="Int Value", default=0)
    float_value: FloatProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="Float Value", default=0)
    string_value: StringProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="String Value")

    @property
    def __data_path__(self) -> str:
        """bpy.context.space_data.show_gizmo -> space_data.show_gizmo"""
        return self.data_path.replace("bpy.context.", "")

    @classmethod
    def clear_info(cls):
        """Clear cached context info."""
        cls.button_pointer = None
        cls.button_prop = None

    @classmethod
    def from_context_get_info(cls, context) -> None:
        """Load info from current context without clearing cached values."""
        pointer = getattr(context, "button_pointer", None)
        prop = getattr(context, "button_prop", None)
        if pointer is not None:
            cls.button_pointer = pointer
        if prop is not None:
            cls.button_prop = prop

    @classmethod
    def _created_element(cls):
        from ...element.element_cure import ElementCURE
        return ElementCURE.ADD.last_element


class Draw(PublicOperator, PublicProperty, OpsProperty):
    def draw(self, context):
        from ...utils.session_state import SessionState

        layout = self.layout.column()
        layout.operator_context = "EXEC_DEFAULT"

        self.update_data(layout, context)

        pref = get_pref()

        pointer = self.button_pointer
        prop = self.button_prop
        if prop and SessionState.context_menu_from_button:
            if not self.data_path:
                self.copy_data_path()

            prop_type = prop.type

            value = getattr(pointer, prop.identifier)

            if self.data_path != "":
                path_box = layout.box()
                path_box.label(text="Data Path")
                path_box.label(text=self.data_path, translate=False)
                context_path = self.__data_path__
                if context_path and context_path != self.data_path:
                    path_box.label(text=f"Context: {context_path}", translate=False)
                layout.separator()

                if prop_type == "BOOLEAN":
                    self.draw_boolean(layout)
                elif prop_type == "INT":
                    self.draw_int(layout)
                elif prop_type == "FLOAT":
                    if prop.is_array:
                        layout.label(text="Array property not supported")
                    else:
                        self.draw_float(layout)
                elif prop_type == "STRING":
                    self.draw_string(layout)
                elif prop_type == "ENUM":
                    if prop.is_enum_flag:
                        layout.alert = True
                        layout.label(text="Multi-select enum (set) is not supported")
                        layout.label(text="Unable to add")
                    else:
                        self.draw_enum(layout)
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

            if self.debug_property.debug_mode and self.data_path:
                layout.label(text=f"data_path:\t{self.data_path}")

    def draw_boolean(self, layout: bpy.types.UILayout):
        layout.label(text="Set Boolean Value")
        for item in self.rna_type.properties["boolean_mode"].enum_items:  # Draw boolean add modes
            ops = layout.operator(CreateElementProperty.bl_idname, text=item.name)
            ops.boolean_mode = item.identifier
            ops.data_path = self.data_path
            ops.property_type = "BOOLEAN"

    def draw_int(self, layout: bpy.types.UILayout):
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

    def draw_float(self, layout: bpy.types.UILayout):
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

    def draw_string(self, layout: bpy.types.UILayout):
        layout.label(text="Modify String")
        layout.separator()
        layout.prop(self, "string_value")
        layout.separator()
        ops = layout.operator(CreateElementProperty.bl_idname, text="Add")
        ops.data_path = self.data_path
        ops.string_value = self.string_value
        ops.property_type = "STRING"

    def draw_enum(self, layout: bpy.types.UILayout):
        layout.label(text="Modify Enumeration")

        layout.separator()
        if not self.has_enum_items:
            layout.alert = True
            layout.label(text="Dynamic enumeration properties cannot be added!!")
            layout.label(text="Unable to add")
            return

        mode_row = layout.row(align=True)
        for identifier, name in self._ENUM_MODE_DRAW_ITEMS:
            mode_row.prop_enum(self, "enum_mode", identifier, text=name)

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
        elif self.enum_mode == "CYCLE":
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
    @staticmethod
    def _set_context_operator(element, op_idname: str, **props) -> None:
        """Assign operator id and properties in a form the UI can read."""
        element.operator_bl_idname = op_idname
        element.operator_properties = str(props) if props else "{}"

    def create_boolean(self):
        """
        bpy.ops.wm.context_set_boolean()
        bpy.ops.wm.context_toggle()
        :return:
        """
        ae = self._created_element()
        if not ae:
            return
        path = self.__data_path__
        bm = self.boolean_mode
        if bm == "SET_TRUE":
            self._set_context_operator(ae, 'wm.context_set_boolean', data_path=path, value=True)
        elif bm == "SET_FALSE":
            self._set_context_operator(ae, 'wm.context_set_boolean', data_path=path, value=False)
        elif bm == "SWITCH":
            self._set_context_operator(ae, 'wm.context_toggle', data_path=path)

    def create_int(self):
        ae = self._created_element()
        from ..modal_mouse import ModalMouseOperator
        if not ae:
            return
        path = self.__data_path__
        vm = self.value_mode
        if vm == "SET_VALUE":
            self._set_context_operator(ae, 'wm.context_set_int', data_path=path, value=self.int_value)
        else:
            ae.operator_bl_idname = (
                f"{ModalMouseOperator.bl_idname}(data_path='{path}', value_mode='{vm}')"
            )

    def create_float(self):
        ae = self._created_element()
        from ..modal_mouse import ModalMouseOperator
        if not ae:
            return
        path = self.__data_path__
        vm = self.value_mode
        if vm == "SET_VALUE":
            self._set_context_operator(ae, 'wm.context_set_float', data_path=path, value=self.float_value)
        else:
            ae.operator_bl_idname = (
                f"{ModalMouseOperator.bl_idname}(data_path='{path}', value_mode='{vm}')"
            )

    def create_string(self):
        """
        bpy.ops.wm.context_set_string()
        :return:
        """
        ae = self._created_element()
        if ae:
            self._set_context_operator(
                ae, 'wm.context_set_string',
                data_path=self.__data_path__,
                value=self.string_value,
            )

    def create_enum(self):
        """
        bpy.ops.wm.context_set_enum(data_path="", value="")
        bpy.ops.wm.context_cycle_enum(data_path="", reverse=False, wrap=False)
        bpy.ops.wm.context_toggle_enum(data_path="", value_1="", value_2="")
        bpy.ops.wm.context_menu_enum(data_path="")
        bpy.ops.wm.context_pie_enum(data_path="")
        :return:
        """
        ae = self._created_element()
        if not ae:
            return
        path = self.__data_path__
        em = self.enum_mode

        if em == "SET":
            self._set_context_operator(ae, 'wm.context_set_enum', data_path=path, value=self.enum_value_a)
        elif em == "CYCLE":
            self._set_context_operator(
                ae, 'wm.context_cycle_enum',
                data_path=path, reverse=self.enum_reverse, wrap=self.enum_wrap,
            )
        elif em == "TOGGLE":
            self._set_context_operator(
                ae, 'wm.context_toggle_enum',
                data_path=path, value_1=self.enum_value_a, value_2=self.enum_value_b,
            )
        elif em == "MENU":
            self._set_context_operator(ae, 'wm.context_menu_enum', data_path=path)
        elif em == "PIE":
            self._set_context_operator(ae, 'wm.context_pie_enum', data_path=path)

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
        pt = self.property_type
        if pt == "ENUM" and self.button_prop and self.button_prop.is_enum_flag:
            self.report({'ERROR'}, "Multi-select enum (set) is not supported")
            return False
        if pt == "ENUM" and not self.has_enum_items:
            self.report({'ERROR'}, "Dynamic enumeration properties cannot be added!!")
            return False
        self.cache_clear()
        with pref.add_element_property.active_radio():
            bpy.ops.wm.gesture_element_add(element_type="OPERATOR")
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

            ae = self._created_element()
            if ae and self.button_prop:
                ae.name = self.__prop_name__
        return True

    @property
    def __prop_name__(self) -> str:
        """Property display name."""
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
    bl_idname = 'wm.gesture_create_element_property'
    bl_description = 'Add a gesture element from a right-clicked property button'
    bl_options = {'REGISTER'}

    button_pointer = None
    button_prop = None

    @classmethod
    def poll(cls, context) -> bool:
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        if not button_pointer or not button_prop:
            cls.poll_message_set("Right-click a property button in the UI")
            return False
        return True

    def invoke(self, context, event) -> set[str]:
        self.from_context_get_info(context)
        self.copy_data_path()
        self.init_string()
        self.init_enum()
        return context.window_manager.invoke_popup(**{'operator': self, 'width': 400})

    def execute(self, context) -> set[str]:
        from ...utils.session_state import SessionState
        SessionState.context_menu_from_button = False

        self.from_context_get_info(context)
        if not self.button_pointer or not self.button_prop:
            self.report({'ERROR'}, "Property context lost, right-click the property again")
            return {'CANCELLED'}

        debug_print(
            "\nexecute", self.data_path,
            self.button_pointer.__class__.__name__,
            self.button_prop.identifier,
            key='operator',
        )
        try:
            ok = self.create()
        finally:
            self.clear_info()
        return {'FINISHED'} if ok else {'CANCELLED'}

    def copy_data_path(self) -> None:
        """Resolve bpy.context-style RNA path for wm.context_* operators."""
        pointer = self.button_pointer
        prop_identifier = self.button_prop.identifier
        pointer_name = pointer.__class__.__name__
        id_data_type = type(pointer.id_data)

        if id_data_type is bpy.types.Mesh:
            self.data_path = f"bpy.context.object.data.{prop_identifier}"
            return
        if id_data_type is bpy.types.Text and bpy.context.area.ui_type == "TEXT_EDITOR":
            self.data_path = f"bpy.context.space_data.text.{prop_identifier}"
            return
        if pointer_name == "View3DShading" and bpy.context.area.ui_type == "PROPERTIES":
            self.data_path = f"bpy.context.scene.display.shading.{prop_identifier}"
            return
        view_layer_path = resolve_view_layer_data_path(pointer, prop_identifier)
        if view_layer_path:
            self.data_path = view_layer_path
            return
        id_data_path = resolve_id_data_context_path(pointer, prop_identifier)
        if id_data_path:
            self.data_path = id_data_path
            return
        if pointer_name in CREATE_ELEMENT_DATA_PATHS:
            self.data_path = f"{CREATE_ELEMENT_DATA_PATHS[pointer_name]}.{prop_identifier}"
            return
        if pointer_name == 'Brush' and bpy.context.object:
            mode = UnifiedPaintPanel.get_brush_mode(bpy.context)
            if mode in CREATE_ELEMENT_BRUSH_PATH:
                self.data_path = f"{CREATE_ELEMENT_BRUSH_PATH[mode]}.{prop_identifier}"
                return

        resolved = resolve_context_data_path(pointer, prop_identifier)
        if resolved:
            self.data_path = resolved
            return

        cp = bpy.ops.ui.copy_data_path_button
        if cp.poll():
            cp(full_path=True)
            clipboard = bpy.context.window_manager.clipboard
            converted = convert_data_path_to_context(clipboard, pointer)
            if converted:
                debug_print("use clipboard", converted, key='operator')
                self.data_path = converted
                return
            normalized = normalize_context_data_path(clipboard)
            if normalized:
                debug_print("use clipboard", normalized, key='operator')
                self.data_path = normalized
                return

    def init_string(self):
        prop = self.button_prop
        if prop and prop.type == "STRING":
            self.string_value = getattr(self.button_pointer, prop.identifier, "")

    def init_enum(self):
        prop = self.button_prop
        pointer = self.button_pointer
        if not prop or not pointer or prop.type != "ENUM" or prop.is_enum_flag:
            return
        current = getattr(pointer, prop.identifier, None)
        if isinstance(current, str) and current:
            self.enum_value_a = current

    def update_data(self, layout, context):
        """Update property from context."""
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
