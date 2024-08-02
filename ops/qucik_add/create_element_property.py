import bpy
from bl_ui.properties_paint_common import UnifiedPaintPanel
from bpy.app.translations import pgettext
from bpy.props import EnumProperty, StringProperty

from ...utils.public import get_pref, PublicOperator, PublicProperty

DATA_PATHS = dict(
    View3DShading="bpy.context.space_data.shading",
    View3DOverlay="bpy.context.space_data.overlay",
    View3DCursor="bpy.context.scene.cursor",
    ToolSettings="bpy.context.tool_settings",
    RenderSettings="bpy.context.scene.render",
    TransformOrientationSlot="bpy.context.scene.transform_orientation_slots[0]",

    BrushGpencilSettings="bpy.context.tool_settings.brush.gpencil_settings",
    UnifiedPaintSettings="bpy.context.tool_settings.unified_paing_settings",

    SpaceUVEditor="bpy.context.space_data.uv_editor",
    SpaceTextEditor="bpy.context.space_data",
    SpaceDopeSheetEditor="bpy.context.space_data",
    SpaceImageEditor="bpy.context.space_data",
    SpaceView3D="bpy.context.space_data",
    SpaceOutliner="bpy.context.space_data",

    Scene="bpy.context.scene",
    Screen="bpy.context.screen",
    World="bpy.context.scene.world",
    WorkSpace="bpy.context.workspace",
    Object="bpy.context.object",
    Material="bpy.context.object.active_material",
    Area="bpy.context.area",
    Region="bpy.context.region",
    GPUFXSettings="bpy.context.space_data.fx_settings",
    GPUSSAOSettings="bpy.context.space_data.fx_settings.ssao",
    GPUDOFSettings="bpy.context.space_data.fx_settings.dof",
    DopeSheet="bpy.context.space_data.dopesheet",
    FileSelectParams="bpy.context.space_data.params",
    SceneEEVEE="bpy.context.scene.eevee",
    CyclesRenderSettings="bpy.context.scene.cycles",
    SceneDisplay="bpy.context.scene.display",

    Preferences="bpy.context.preferences",
    PreferencesInput="bpy.context.preferences.inputs",
    PreferencesEdit="bpy.context.preferences.edit",
    PreferencesFilePaths="bpy.context.preferences.filepaths",
    PreferencesSystem="bpy.context.preferences.system",
    PreferencesView="bpy.context.preferences.view",

    GpPaint="bpy.context.tool_settings.gpencil_paint",
    GPencilSculptSettings="bpy.context.tool_settings.gpencil_sculpt",

    ColorManagedViewSettings="bpy.context.scene.view_settings",
    ViewLayer="bpy.context.scene.view_layers",
    UnitSettings="bpy.context.scene.unit_settings",
    RigidBodyWorld="bpy.context.scene.rigidbody_world",

    ImagePaint="bpy.context.tool_settings.image_paint",
    BrushTextureSlot="bpy.context.tool_settings.image_paint.brush.texture_slot",

    WindowManager="bpy.context.window_manager",
)
BRUSH_PATH = dict(
    # 3D paint settings
    SCULPT='bpy.context.tool_settings.sculpt',
    PAINT_VERTEX='bpy.context.tool_settings.vertex_paint',
    PAINT_WEIGHT='bpy.context.tool_settings.weight_paint',
    PAINT_TEXTURE='bpy.context.tool_settings.image_paint',
    PARTICLE='bpy.context.tool_settings.particle_edit',

    # 2D paint settings
    PAINT_2D='bpy.context.tool_settings.image_paint',
    # Grease Pencil settings
    PAINT_GPENCIL='bpy.context.tool_settings.gpencil_paint',
    SCULPT_GPENCIL='bpy.context.tool_settings.gpencil_sculpt_paint',
    WEIGHT_GPENCIL='bpy.context.tool_settings.gpencil_weight_paint',
    VERTEX_GPENCIL='bpy.context.tool_settings.gpencil_vertex_paint',
    SCULPT_CURVES='bpy.context.tool_settings.curves_sculpt',
    PAINT_GREASE_PENCIL='bpy.context.tool_settings.gpencil_paint',
    SCULPT_GREASE_PENCIL='bpy.context.tool_settings.gpencil_sculpt_paint',

    WEIGHT_GREASE_PENCIL='bpy.context.tool_settings.gpencil_weight_paint',
)


class ElementProperty(PublicOperator, PublicProperty):
    def draw(self, context):
        layout = self.layout.column()
        layout.operator_context = "EXEC_DEFAULT"

        pointer = self.button_pointer
        prop = self.button_prop
        layout.context_pointer_set('button_pointer', pointer)
        layout.context_pointer_set('button_prop', prop)
        layout.context_pointer_set('show_gesture_add_menu', self)

        pref = get_pref()

        if prop:
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
        for item in self.rna_type.properties["boolean_mode"].enum_items:
            ops = layout.operator(CreateElementProperty.bl_idname, text=item.name)
            ops.boolean_mode = item.identifier
            ops.data_path = self.data_path

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


class CreateElementProperty(ElementProperty):
    bl_label = '创建属性元素'
    bl_idname = 'gesture.create_element_property'
    # bl_options = {'REGISTER', 'UNDO'}

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

        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 600})

    def execute(self, context) -> set[str]:
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
        elif pointer_name in DATA_PATHS:
            self.data_path = f"{DATA_PATHS[pointer_name]}.{prop_identifier}"
            return
        elif pointer_name == 'Brush' and bpy.context.object:
            mode = UnifiedPaintPanel.get_brush_mode(bpy.context)
            if mode in BRUSH_PATH:
                self.data_path = f"{BRUSH_PATH[mode]}.{prop_identifier}"
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
