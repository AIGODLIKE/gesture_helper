# 使用右键创建元素时对应类的数据路径
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
    "SceneDisplay": "bpy.context.scene.display",

    "Preferences": "bpy.context.preferences",
    "PreferencesInput": "bpy.context.preferences.inputs",
    "PreferencesEdit": "bpy.context.preferences.edit",
    "PreferencesFilePaths": "bpy.context.preferences.filepaths",
    "PreferencesSystem": "bpy.context.preferences.system",
    "PreferencesView": "bpy.context.preferences.view",

    "GpPaint": "bpy.context.tool_settings.gpencil_paint",
    "GPencilSculptSettings": "bpy.context.tool_settings.gpencil_sculpt",

    "ColorManagedViewSettings": "bpy.context.scene.view_settings",
    "ViewLayer": "bpy.context.scene.view_layers",
    "UnitSettings": "bpy.context.scene.unit_settings",
    "RigidBodyWorld": "bpy.context.scene.rigidbody_world",

    "ImagePaint": "bpy.context.tool_settings.image_paint",
    "BrushTextureSlot": "bpy.context.tool_settings.image_paint.brush.texture_slot",

    "WindowManager": "bpy.context.window_manager",
}

# 使用右键创建元素笔刷使用的数据
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
