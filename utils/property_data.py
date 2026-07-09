# RNA data paths for context-menu element creation
CREATE_ELEMENT_DATA_PATHS = {
    "View3DShading": "bpy.context.space_data.shading",
    "View3DOverlay": "bpy.context.space_data.overlay",
    "View3DCursor": "bpy.context.scene.cursor",
    "ToolSettings": "bpy.context.tool_settings",
    "RenderSettings": "bpy.context.scene.render",
    "TransformOrientationSlot": "bpy.context.scene.transform_orientation_slots[0]",

    "BrushGpencilSettings": "bpy.context.tool_settings.brush.gpencil_settings",
    "UnifiedPaintSettings": "bpy.context.tool_settings.unified_paing_settings",

    "SpaceUVEditor": "bpy.context.space_data.uv_editor",
    "SpaceTextEditor": "bpy.context.space_data",
    "SpaceNodeEditor": "bpy.context.space_data",
    "SpaceDopeSheetEditor": "bpy.context.space_data",
    "SpaceImageEditor": "bpy.context.space_data",
    "SpaceView3D": "bpy.context.space_data",
    "SpaceOutliner": "bpy.context.space_data",

    "Scene": "bpy.context.scene",
    "Screen": "bpy.context.screen",
    "World": "bpy.context.scene.world",
    "WorkSpace": "bpy.context.workspace",
    "Object": "bpy.context.object",
    "Material": "bpy.context.object.active_material",
    "Area": "bpy.context.area",
    "Region": "bpy.context.region",
    "GPUFXSettings": "bpy.context.space_data.fx_settings",
    "GPUSSAOSettings": "bpy.context.space_data.fx_settings.ssao",
    "GPUDOFSettings": "bpy.context.space_data.fx_settings.dof",
    "DopeSheet": "bpy.context.space_data.dopesheet",
    "FileSelectParams": "bpy.context.space_data.params",
    "SceneEEVEE": "bpy.context.scene.eevee",
    "CyclesRenderSettings": "bpy.context.scene.cycles",
    "CyclesObjectSettings": "bpy.context.object.cycles",
    "SceneDisplay": "bpy.context.scene.display",

    "Preferences": "bpy.context.preferences",
    "PreferencesInput": "bpy.context.preferences.inputs",
    "PreferencesEdit": "bpy.context.preferences.edit",
    "PreferencesFilePaths": "bpy.context.preferences.filepaths",
    "PreferencesSystem": "bpy.context.preferences.system",
    "PreferencesView": "bpy.context.preferences.view",

    "GpPaint": "bpy.context.tool_settings.gpencil_paint",
    "GPencilLayer": "bpy.context.active_annotation_layer",
    "GPencilSculptSettings": "bpy.context.tool_settings.gpencil_sculpt",

    "ColorManagedViewSettings": "bpy.context.scene.view_settings",
    "ViewLayer": "bpy.context.view_layer",
    "UnitSettings": "bpy.context.scene.unit_settings",
    "RigidBodyWorld": "bpy.context.scene.rigidbody_world",

    "ImagePaint": "bpy.context.tool_settings.image_paint",
    "BrushTextureSlot": "bpy.context.tool_settings.image_paint.brush.texture_slot",

    "WindowManager": "bpy.context.window_manager",
}

# Brush data for context-menu element creation
CREATE_ELEMENT_BRUSH_PATH = {
    # 3D paint settings
    "SCULPT": 'bpy.context.tool_settings.sculpt',
    "PAINT_VERTEX": 'bpy.context.tool_settings.vertex_paint',
    "PAINT_WEIGHT": 'bpy.context.tool_settings.weight_paint',
    "PAINT_TEXTURE": 'bpy.context.tool_settings.image_paint',
    "PARTICLE": 'bpy.context.tool_settings.particle_edit',

    # 2D paint settings
    "PAINT_2D": 'bpy.context.tool_settings.image_paint',
    # Grease Pencil settings
    "PAINT_GPENCIL": 'bpy.context.tool_settings.gpencil_paint',
    "SCULPT_GPENCIL": 'bpy.context.tool_settings.gpencil_sculpt_paint',
    "WEIGHT_GPENCIL": 'bpy.context.tool_settings.gpencil_weight_paint',
    "VERTEX_GPENCIL": 'bpy.context.tool_settings.gpencil_vertex_paint',
    "SCULPT_CURVES": 'bpy.context.tool_settings.curves_sculpt',
    "PAINT_GREASE_PENCIL": 'bpy.context.tool_settings.gpencil_paint',
    "SCULPT_GREASE_PENCIL": 'bpy.context.tool_settings.gpencil_sculpt_paint',

    "WEIGHT_GREASE_PENCIL": 'bpy.context.tool_settings.gpencil_weight_paint',
}


def normalize_context_data_path(path: str) -> str | None:
    """Keep bpy.context-style paths; reject bpy.data absolute paths."""
    if not path or not str(path).strip():
        return None
    text = str(path).strip()
    if text.startswith('bpy.data.'):
        return None
    if text.startswith('bpy.context.'):
        return text
    if text.startswith('context.'):
        return f"bpy.{text}"
    return f"bpy.context.{text}"


def convert_data_path_to_context(path: str, pointer=None) -> str | None:
    """Convert bpy.data.objects[...] paths to bpy.context.object when it is active."""
    import ast
    import re

    import bpy

    text = str(path).strip()
    if not text:
        return None
    if text.startswith('bpy.context.'):
        return text

    match = re.fullmatch(r'bpy\.data\.objects\[([^\]]+)\]\.(.*)', text)
    if match:
        try:
            name = ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError):
            name = match.group(1).strip('"\'')
        rest = match.group(2)
        obj = bpy.context.object
        if obj is not None and obj.name == name:
            return f"bpy.context.object.{rest}"
        id_data = getattr(pointer, 'id_data', None) if pointer is not None else None
        if isinstance(id_data, bpy.types.Object) and id_data.name == name and obj == id_data:
            return f"bpy.context.object.{rest}"
        return None

    if text.startswith('bpy.data.'):
        return None
    return normalize_context_data_path(text)


def resolve_id_data_context_path(pointer, prop_identifier: str) -> str | None:
    """Map nested RNA pointers (e.g. object.cycles) to bpy.context.* paths."""
    import bpy

    if pointer is None or not hasattr(pointer, 'id_data'):
        return None

    id_data = pointer.id_data
    context = bpy.context

    try:
        rel = pointer.path_from_id() or ""
    except (AttributeError, RuntimeError, TypeError, ValueError):
        rel = ""

    suffix = f"{rel}.{prop_identifier}" if rel else prop_identifier

    if isinstance(id_data, bpy.types.Object) and context.object == id_data:
        return f"bpy.context.object.{suffix}"
    if isinstance(id_data, bpy.types.Scene) and context.scene == id_data:
        return f"bpy.context.scene.{suffix}"
    if isinstance(id_data, bpy.types.World) and context.scene and context.scene.world == id_data:
        return f"bpy.context.scene.world.{suffix}"
    if isinstance(id_data, bpy.types.Mesh) and context.object and context.object.data == id_data:
        return f"bpy.context.object.data.{suffix}"
    if isinstance(id_data, bpy.types.Material):
        obj = context.object
        if obj and obj.active_material == id_data:
            return f"bpy.context.object.active_material.{suffix}"
    return None


def resolve_view_layer_data_path(pointer, prop_identifier: str) -> str | None:
    """Map a ViewLayer pointer to bpy.context.view_layer or a named layer path."""
    import bpy
    if not isinstance(pointer, bpy.types.ViewLayer):
        return None
    context = bpy.context
    active = context.view_layer
    if pointer == active:
        return f"bpy.context.view_layer.{prop_identifier}"
    scene = context.scene
    if scene is None:
        return None
    for view_layer in scene.view_layers:
        if view_layer == pointer:
            return f'bpy.context.scene.view_layers["{view_layer.name}"].{prop_identifier}'
    return None


def resolve_context_data_path(pointer, prop_identifier: str) -> str | None:
    """Map a live RNA pointer to bpy.context.* when it matches current context."""
    import bpy
    context = bpy.context
    view_layer_path = resolve_view_layer_data_path(pointer, prop_identifier)
    if view_layer_path:
        return view_layer_path

    id_data_path = resolve_id_data_context_path(pointer, prop_identifier)
    if id_data_path:
        return id_data_path

    for name in (
        'object', 'scene', 'view_layer', 'space_data', 'tool_settings',
        'area', 'region', 'screen', 'workspace', 'preferences', 'window_manager',
    ):
        ctx_item = getattr(context, name, None)
        if ctx_item is not None and pointer == ctx_item:
            return f"bpy.context.{name}.{prop_identifier}"

    for base_path in CREATE_ELEMENT_DATA_PATHS.values():
        rel = base_path
        if rel.startswith('bpy.context.'):
            rel = rel[len('bpy.context.'):]
        try:
            target = context.path_resolve(rel)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        if pointer == target:
            return f"{base_path}.{prop_identifier}"
    return None
