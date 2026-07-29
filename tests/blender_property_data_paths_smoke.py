"""Run with Blender to validate context property paths against live RNA."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

from gesture_helper.ops.quick_add import (  # noqa: E402
    create_element_property as create_property_module,
)
from gesture_helper.utils.property_data import (  # noqa: E402
    CREATE_ELEMENT_DATA_PATHS,
    _has_numeric_rna_path_index,
    can_use_clipboard_context_fallback,
    resolve_context_data_path,
    resolve_id_data_context_path,
    validate_context_data_path,
)


assert _has_numeric_rna_path_index("items[1]")
assert _has_numeric_rna_path_index("items[-1]")
assert _has_numeric_rna_path_index("[0]")
assert not _has_numeric_rna_path_index('items["Item[1]"]')
assert not _has_numeric_rna_path_index('["Item[1]"]')


SCALAR_TYPES = {'BOOLEAN', 'INT', 'FLOAT', 'ENUM', 'STRING'}
PATH_EXCEPTIONS = (
    AttributeError,
    KeyError,
    ReferenceError,
    RuntimeError,
    TypeError,
    ValueError,
)


def pointer_address(pointer):
    try:
        return pointer.as_pointer()
    except PATH_EXCEPTIONS:
        return 0


def context_path_resolve(path):
    return bpy.types.Context.path_resolve(bpy.context, path)


def keyed_owner(base, key):
    escaped_key = bpy.utils.escape_identifier(key)
    return f'{base}["{escaped_key}"]'


def rna_is_a(rna, identifier):
    while rna is not None:
        if rna.identifier == identifier:
            return True
        rna = rna.base
    return False


def sample_property(pointer):
    fallback = None
    for prop in pointer.bl_rna.properties:
        if (
                prop.identifier == 'rna_type'
                or prop.type not in SCALAR_TYPES
                or getattr(prop, 'is_array', False)
        ):
            continue
        if fallback is None:
            fallback = prop.identifier
        if not getattr(prop, 'is_readonly', False):
            return prop.identifier
    return fallback


def assert_resolves(pointer, owner_path=None, prop_identifier=None):
    prop_identifier = prop_identifier or sample_property(pointer)
    assert prop_identifier is not None, pointer.bl_rna.identifier
    data_path = resolve_context_data_path(pointer, prop_identifier)
    assert data_path is not None, (pointer.bl_rna.identifier, prop_identifier)
    assert validate_context_data_path(pointer, prop_identifier, data_path), data_path
    if owner_path is not None:
        assert data_path == f"{owner_path}.{prop_identifier}", data_path
    relative_owner = data_path.removeprefix("bpy.context.").rpartition('.')[0]
    resolved_owner = context_path_resolve(relative_owner)
    assert pointer_address(resolved_owner) == pointer_address(pointer), data_path
    return data_path


def activate_object(obj):
    for selected in tuple(bpy.context.selected_objects):
        selected.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


scene = bpy.context.scene
if scene.world is None:
    scene.world = bpy.data.worlds.new("Gesture Helper Path World")

mesh = bpy.data.meshes.new("Gesture Helper Path Mesh")
mesh.from_pydata([(0.0, 0.0, 0.0)], [], [])
obj = bpy.data.objects.new("Gesture Helper Path Object", mesh)
scene.collection.objects.link(obj)
material = bpy.data.materials.new("Gesture Helper Path Material")
mesh.materials.append(material)
activate_object(obj)

# Brush paths must follow the active paint mode before the generic resolver.
# Blender 4.2 shares its default Draw brush between vertex and weight paint,
# which exposes a wrong-priority regression without modifying user data.
window = bpy.context.window
screen = window.screen
brush_area = max(screen.areas, key=lambda item: item.width * item.height)
original_brush_area_type = brush_area.type
try:
    brush_area.type = 'VIEW_3D'
    brush_region = next(
        item for item in brush_area.regions if item.type == 'WINDOW'
    )
    with bpy.context.temp_override(
            window=window,
            screen=screen,
            area=brush_area,
            region=brush_region):
        activate_object(obj)
        assert bpy.ops.object.mode_set(mode='WEIGHT_PAINT') == {'FINISHED'}
        try:
            if bpy.app.version >= (4, 3, 0):
                # Brush assets replaced writable Paint.brush pointers in 4.3.
                # Blender 4.3/4.4 may return CANCELLED while still activating
                # the asset, so the live pointer below is authoritative.
                bpy.ops.brush.asset_activate(
                    asset_library_type='ESSENTIALS',
                    relative_asset_identifier=(
                        "brushes/essentials_brushes-mesh_weight.blend"
                        "/Brush/Paint"
                    ),
                )
            brush = bpy.context.tool_settings.weight_paint.brush
            assert brush is not None
            if bpy.app.version < (4, 3, 0):
                assert brush == bpy.context.tool_settings.vertex_paint.brush
            brush_probe = SimpleNamespace(
                data_path="",
                button_pointer=brush,
                button_prop=brush.bl_rna.properties['size'],
            )
            create_property_module.CreateElementProperty.copy_data_path(
                brush_probe,
            )
            assert brush_probe.data_path == (
                "bpy.context.tool_settings.weight_paint.brush.size"
            ), brush_probe.data_path
        finally:
            if obj.mode != 'OBJECT':
                assert bpy.ops.object.mode_set(mode='OBJECT') == {'FINISHED'}
finally:
    brush_area.type = original_brush_area_type


# copy_data_path_button requires a hovered UI button and cannot be polled in a
# background smoke run. Exercise the operator's orchestration with local fakes
# while keeping Blender's path resolver coverage live elsewhere in this file.
clipboard_pointer = SimpleNamespace()
clipboard_prop = SimpleNamespace(identifier="hide_viewport")
clipboard_sentinel = "Gesture Helper Clipboard Sentinel"
valid_clipboard_path = "bpy.context.object.hide_viewport"
invalid_clipboard_path = "bpy.context.scene.frame_start"
patched_names = (
    "bpy",
    "resolve_context_data_path",
    "can_use_clipboard_context_fallback",
    "convert_data_path_to_context",
    "normalize_context_data_path",
    "validate_context_data_path",
)
original_operator_globals = {
    name: getattr(create_property_module, name) for name in patched_names
}


def run_clipboard_case(
        *, result, converted, normalized, valid_paths=(), error=None):
    calls = []
    window_manager = SimpleNamespace(clipboard=clipboard_sentinel)

    class FakeCopyDataPathButton:
        @staticmethod
        def poll():
            calls.append(("poll",))
            return True

        def __call__(self, *, full_path):
            calls.append(("copy", full_path))
            window_manager.clipboard = "copied data path"
            if error is not None:
                raise error
            return result

    create_property_module.bpy = SimpleNamespace(
        context=SimpleNamespace(window_manager=window_manager),
        ops=SimpleNamespace(
            ui=SimpleNamespace(
                copy_data_path_button=FakeCopyDataPathButton(),
            ),
        ),
    )

    def convert_path(value, pointer):
        calls.append(("convert", value))
        assert pointer is clipboard_pointer
        return converted

    def normalize_path(value):
        calls.append(("normalize", value))
        return normalized

    def validate_path(pointer, prop_identifier, candidate):
        calls.append(("validate", candidate))
        assert pointer is clipboard_pointer
        assert prop_identifier == clipboard_prop.identifier
        return candidate in valid_paths

    create_property_module.convert_data_path_to_context = convert_path
    create_property_module.normalize_context_data_path = normalize_path
    create_property_module.validate_context_data_path = validate_path
    probe = SimpleNamespace(
        data_path="stale",
        button_pointer=clipboard_pointer,
        button_prop=clipboard_prop,
    )
    caught = None
    try:
        create_property_module.CreateElementProperty.copy_data_path(probe)
    except Exception as exc:  # The exception case verifies finally restoration.
        caught = exc
    assert window_manager.clipboard == clipboard_sentinel
    return probe.data_path, calls, caught


try:
    create_property_module.resolve_context_data_path = lambda *_args: None
    create_property_module.can_use_clipboard_context_fallback = (
        lambda *_args: True
    )

    data_path, calls, caught = run_clipboard_case(
        result={'FINISHED'},
        converted=valid_clipboard_path,
        normalized=invalid_clipboard_path,
        valid_paths={valid_clipboard_path},
    )
    assert caught is None
    assert data_path == valid_clipboard_path
    assert calls == [
        ("poll",),
        ("copy", True),
        ("convert", "copied data path"),
        ("normalize", "copied data path"),
        ("validate", valid_clipboard_path),
    ]

    data_path, calls, caught = run_clipboard_case(
        result={'FINISHED'},
        converted=valid_clipboard_path,
        normalized=invalid_clipboard_path,
    )
    assert caught is None
    assert data_path == ""
    assert calls[-2:] == [
        ("validate", valid_clipboard_path),
        ("validate", invalid_clipboard_path),
    ]

    data_path, calls, caught = run_clipboard_case(
        result={'CANCELLED'},
        converted=valid_clipboard_path,
        normalized=invalid_clipboard_path,
    )
    assert caught is None
    assert data_path == ""
    assert calls == [("poll",), ("copy", True)]

    copy_error = RuntimeError("copy data path failed")
    data_path, calls, caught = run_clipboard_case(
        result={'FINISHED'},
        converted=valid_clipboard_path,
        normalized=invalid_clipboard_path,
        error=copy_error,
    )
    assert caught is copy_error
    assert data_path == ""
    assert calls == [("poll",), ("copy", True)]
finally:
    for name, value in original_operator_globals.items():
        setattr(create_property_module, name, value)

# Regression cases that previously collapsed nested pointers to the Scene/Mesh.
assert_resolves(scene.display, "bpy.context.scene.display", "shadow_shift")
assert resolve_id_data_context_path(scene.display, "shadow_shift") is None
assert_resolves(scene.safe_areas, "bpy.context.scene.safe_areas", "title")
assert_resolves(
    bpy.context.tool_settings.custom_bevel_profile_preset,
    "bpy.context.tool_settings.custom_bevel_profile_preset",
    "use_clip",
)
assert_resolves(
    bpy.context.view_layer.freestyle_settings,
    "bpy.context.view_layer.freestyle_settings",
    "crease_angle",
)
assert_resolves(mesh, "bpy.context.object.data")
mesh_vertex = mesh.vertices[0]
assert resolve_context_data_path(mesh_vertex, "hide") is None
assert resolve_id_data_context_path(mesh_vertex, "hide") is None
assert not can_use_clipboard_context_fallback(mesh_vertex)
material_slot = obj.material_slots[0]
assert resolve_context_data_path(material_slot, "link") is None
assert resolve_id_data_context_path(material_slot, "link") is None
assert not can_use_clipboard_context_fallback(material_slot)

for index, slot in enumerate(scene.transform_orientation_slots):
    assert_resolves(
        slot,
        f"bpy.context.scene.transform_orientation_slots[{index}]",
    )

# The generic ID anchor must support every active Object.data subtype, not Mesh only.
data_blocks = (
    (bpy.data.cameras.new("Gesture Helper Path Camera"), "lens"),
    (bpy.data.lights.new("Gesture Helper Path Light", 'POINT'), "energy"),
    (bpy.data.armatures.new("Gesture Helper Path Armature"), "display_type"),
    (bpy.data.curves.new("Gesture Helper Path Curve", 'CURVE'), "resolution_u"),
    (bpy.data.lattices.new("Gesture Helper Path Lattice"), "points_u"),
    (bpy.data.metaballs.new("Gesture Helper Path Metaball"), "resolution"),
    (bpy.data.speakers.new("Gesture Helper Path Speaker"), "volume"),
)
for data, prop_identifier in data_blocks:
    data_obj = bpy.data.objects.new(f"{data.name} Object", data)
    scene.collection.objects.link(data_obj)
    activate_object(data_obj)
    assert_resolves(data, "bpy.context.object.data", prop_identifier)

inactive_camera = bpy.data.cameras.new("Gesture Helper Inactive Camera")
assert resolve_context_data_path(inactive_camera, "lens") is None

removed_object = bpy.data.objects.new("Gesture Helper Removed Object", None)
scene.collection.objects.link(removed_object)
bpy.data.objects.remove(removed_object, do_unlink=True)
assert resolve_context_data_path(removed_object, "hide_viewport") is None
assert resolve_id_data_context_path(removed_object, "hide_viewport") is None
assert not can_use_clipboard_context_fallback(removed_object)
assert not validate_context_data_path(
    removed_object,
    "hide_viewport",
    "bpy.context.object.hide_viewport",
)
del removed_object
activate_object(obj)

# All concrete editor Space classes must be present, including new Blender types.
space_identifiers = {
    rna_type.bl_rna.identifier
    for name in dir(bpy.types)
    if (rna_type := getattr(bpy.types, name, None)) is not None
    and getattr(rna_type, "bl_rna", None) is not None
    and rna_type.bl_rna.base is not None
    and rna_type.bl_rna.base.identifier == "Space"
}
assert space_identifiers <= CREATE_ELEMENT_DATA_PATHS.keys(), (
    space_identifiers - CREATE_ELEMENT_DATA_PATHS.keys()
)
assert not {
    "GPUFXSettings", "GPUSSAOSettings", "GPUDOFSettings",
} & CREATE_ELEMENT_DATA_PATHS.keys()
assert "ID" not in CREATE_ELEMENT_DATA_PATHS
assert not any(
    path.endswith(".eraser_brush") or ".eraser_brush." in path
    for candidates in CREATE_ELEMENT_DATA_PATHS.values()
    for path in candidates
)

theme = bpy.context.preferences.themes[0]
assert_resolves(theme, "bpy.context.preferences.themes[0]")
for rna_prop in theme.bl_rna.properties:
    if rna_prop.type != 'POINTER' or rna_prop.identifier == 'rna_type':
        continue
    theme_section = getattr(theme, rna_prop.identifier)
    if theme_section is not None and sample_property(theme_section) is not None:
        assert_resolves(
            theme_section,
            f"bpy.context.preferences.themes[0].{rna_prop.identifier}",
        )
for index, color_set in enumerate(theme.bone_color_sets):
    assert_resolves(
        color_set,
        f"bpy.context.preferences.themes[0].bone_color_sets[{index}]",
        "show_colored_constraints",
    )
assert len(CREATE_ELEMENT_DATA_PATHS["ThemeBoneColorSet"]) == len(
    theme.bone_color_sets
)
assert len(CREATE_ELEMENT_DATA_PATHS["ThemeCollectionColor"]) == len(
    theme.collection_color
)
assert len(CREATE_ELEMENT_DATA_PATHS["ThemeStripColor"]) == len(
    theme.strip_color
)

ui_style = bpy.context.preferences.ui_styles[0]
for rna_prop in ui_style.bl_rna.properties:
    if rna_prop.type == 'POINTER' and rna_prop.identifier != 'rna_type':
        assert_resolves(
            getattr(ui_style, rna_prop.identifier),
            f"bpy.context.preferences.ui_styles[0].{rna_prop.identifier}",
        )
for index, solid_light in enumerate(
        bpy.context.preferences.system.solid_lights):
    assert_resolves(
        solid_light,
        f"bpy.context.preferences.system.solid_lights[{index}]",
        "use",
    )
assert len(CREATE_ELEMENT_DATA_PATHS["UserSolidLight"]) == len(
    bpy.context.preferences.system.solid_lights
)
weight_elements = bpy.context.preferences.view.weight_color_range.elements
original_weight_element_length = len(weight_elements)
assert original_weight_element_length >= 2
previous_weight_element = weight_elements[-2]
last_weight_element = weight_elements[-1]
last_weight_element_position = last_weight_element.position
inserted_weight_element_position = (
    previous_weight_element.position + last_weight_element_position
) / 2.0
unstable_weight_element_path = (
    "preferences.view.weight_color_range.elements"
    f"[{original_weight_element_length - 1}]"
)
assert pointer_address(
    context_path_resolve(unstable_weight_element_path)
) == pointer_address(last_weight_element)
inserted_weight_element = weight_elements.new(inserted_weight_element_position)
try:
    # The old numeric path silently redirects after a sorted insertion.
    redirected_weight_element = context_path_resolve(
        unstable_weight_element_path
    )
    assert redirected_weight_element.position == inserted_weight_element_position
    assert redirected_weight_element.position != last_weight_element_position
    for weight_element in tuple(weight_elements):
        assert resolve_context_data_path(weight_element, "alpha") is None
        assert not can_use_clipboard_context_fallback(weight_element)
finally:
    weight_elements.remove(inserted_weight_element)
assert len(weight_elements) == original_weight_element_length

# Runtime-sized Preferences collection keys can be renamed or duplicated, so
# their elements must fail closed instead of persisting a key or index.
preferences = bpy.context.preferences
script_directories = preferences.filepaths.script_directories
original_length = len(script_directories)
first = script_directories.new()
second = script_directories.new()
first_removed = False
try:
    first.name = 'Gesture "Helper" Script A'
    second.name = 'Gesture "Helper" Script B'
    for script_directory in (first, second):
        assert resolve_context_data_path(
            script_directory, "directory",
        ) is None
        assert not can_use_clipboard_context_fallback(script_directory)
    script_directories.remove(first)
    first_removed = True
    second.name += " Renamed"
    assert resolve_context_data_path(second, "directory") is None
finally:
    if not first_removed:
        script_directories.remove(first)
    script_directories.remove(second)
assert len(script_directories) == original_length

autoexec_paths = preferences.autoexec_paths
original_length = len(autoexec_paths)
first = autoexec_paths.new()
second = autoexec_paths.new()
first_removed = False
try:
    duplicate_path = 'Gesture "Helper" Autoexec Duplicate'
    first.path = duplicate_path
    second.path = duplicate_path
    assert resolve_context_data_path(first, "use_glob") is None
    assert resolve_context_data_path(second, "use_glob") is None
    assert not can_use_clipboard_context_fallback(first)
    assert not can_use_clipboard_context_fallback(second)

    second.path = 'Gesture "Helper" Autoexec Unique'
    assert resolve_context_data_path(second, "use_glob") is None
    autoexec_paths.remove(first)
    first_removed = True
    assert resolve_context_data_path(second, "use_glob") is None
finally:
    if not first_removed:
        autoexec_paths.remove(first)
    autoexec_paths.remove(second)
assert len(autoexec_paths) == original_length

dynamic_preference_cases = (
    (
        preferences.filepaths.asset_libraries,
        lambda suffix: preferences.filepaths.asset_libraries.new(
            name=f'Gesture "Helper" Asset {suffix}',
            directory=str(REPOSITORY),
        ),
        "UserAssetLibrary",
        "import_method",
    ),
    (
        preferences.extensions.repos,
        lambda suffix: preferences.extensions.repos.new(
            name=f'Gesture "Helper" Repo {suffix}',
            module=f"gesture_helper_probe_{suffix.lower()}",
            source='USER',
        ),
        "UserExtensionRepo",
        "enabled",
    ),
)
for collection, create, identifier, prop_identifier in (
        dynamic_preference_cases):
    original_length = len(collection)
    first = create("A")
    second = create("B")
    first_removed = False
    try:
        assert second.bl_rna.identifier == identifier
        assert not second.is_property_readonly(prop_identifier)
        for preference_item in (first, second):
            assert resolve_context_data_path(
                preference_item, prop_identifier,
            ) is None
            assert not can_use_clipboard_context_fallback(preference_item)

        collection.remove(first)
        first_removed = True
        assert resolve_context_data_path(second, prop_identifier) is None

        second.name += " Renamed"
        assert resolve_context_data_path(second, prop_identifier) is None
    finally:
        if not first_removed:
            collection.remove(first)
        collection.remove(second)
    assert len(collection) == original_length

# Arbitrary PropertyGroup collection names can later collide, while their
# numeric path_from_id() path redirects after earlier items are removed.
class GestureHelperScenePathItem(bpy.types.PropertyGroup):
    pass


GestureHelperScenePathItem.__annotations__ = {
    "name": bpy.props.StringProperty(),
    "value": bpy.props.BoolProperty(),
}
bpy.utils.register_class(GestureHelperScenePathItem)
bpy.types.Scene.gesture_helper_path_items = bpy.props.CollectionProperty(
    type=GestureHelperScenePathItem,
)
try:
    scene_path_items = scene.gesture_helper_path_items
    for name in (
            'Gesture "Helper" Scene A',
            'Gesture "Helper" Scene B',
            'Gesture "Helper" Scene C',
    ):
        scene_path_items.add().name = name

    numeric_scene_item_path = "scene.gesture_helper_path_items[1]"
    assert context_path_resolve(numeric_scene_item_path).name.endswith("B")
    for scene_path_item in tuple(scene_path_items):
        assert resolve_context_data_path(scene_path_item, "value") is None
        assert resolve_id_data_context_path(scene_path_item, "value") is None
        assert not can_use_clipboard_context_fallback(scene_path_item)

    scene_path_items.remove(0)
    assert context_path_resolve(numeric_scene_item_path).name.endswith("C")
    for scene_path_item in tuple(scene_path_items):
        assert resolve_context_data_path(scene_path_item, "value") is None
        assert not can_use_clipboard_context_fallback(scene_path_item)
finally:
    scene.gesture_helper_path_items.clear()
    del bpy.types.Scene.gesture_helper_path_items
    bpy.utils.unregister_class(GestureHelperScenePathItem)

# Add-on preference classes are registered dynamically and may contain nested
# PropertyGroups. At least one built-in add-on must resolve through its module.
resolved_addon_preferences = 0
for addon in preferences.addons:
    try:
        addon_preferences = addon.preferences
    except PATH_EXCEPTIONS:
        continue
    if addon_preferences is None:
        continue
    prop_identifier = sample_property(addon_preferences)
    if prop_identifier is None:
        continue
    owner_path = keyed_owner(
        "bpy.context.preferences.addons",
        addon.module,
    ) + ".preferences"
    assert_resolves(addon_preferences, owner_path, prop_identifier)
    resolved_addon_preferences += 1
assert resolved_addon_preferences >= 1

# Moving one RNA item type from an unsafe collection to a stable pointer on a
# newly registered AddonPreferences owner must replace the stale recipe.
class GestureHelperCacheItem(bpy.types.PropertyGroup):
    pass


GestureHelperCacheItem.__annotations__ = {
    "name": bpy.props.StringProperty(),
    "value": bpy.props.BoolProperty(),
}


class GestureHelperCachePreferencesA(bpy.types.AddonPreferences):
    bl_idname = "gesture_helper_cache_a"

    def draw(self, context):
        pass


GestureHelperCachePreferencesA.__annotations__ = {
    "items": bpy.props.CollectionProperty(type=GestureHelperCacheItem),
}
bpy.utils.register_class(GestureHelperCacheItem)
bpy.utils.register_class(GestureHelperCachePreferencesA)
cache_addon = preferences.addons.new()
cache_addon.module = GestureHelperCachePreferencesA.bl_idname
try:
    cache_item = cache_addon.preferences.items.add()
    cache_item.name = 'Gesture "Helper" Cache A'
    assert resolve_context_data_path(cache_item, "value") is None
    assert not can_use_clipboard_context_fallback(cache_item)
finally:
    preferences.addons.remove(cache_addon)
    bpy.utils.unregister_class(GestureHelperCachePreferencesA)


class GestureHelperCachePreferencesB(bpy.types.AddonPreferences):
    bl_idname = "gesture_helper_cache_b"

    def draw(self, context):
        pass


GestureHelperCachePreferencesB.__annotations__ = {
    "config": bpy.props.PointerProperty(type=GestureHelperCacheItem),
}
bpy.utils.register_class(GestureHelperCachePreferencesB)
cache_addon = preferences.addons.new()
cache_addon.module = GestureHelperCachePreferencesB.bl_idname
try:
    cache_item = cache_addon.preferences.config
    cache_b_owner = keyed_owner(
        "bpy.context.preferences.addons",
        cache_addon.module,
    ) + ".preferences.config"
    assert_resolves(
        cache_item,
        cache_b_owner,
        "value",
    )
    assert all(
        "gesture_helper_cache_a" not in candidate
        for candidates in CREATE_ELEMENT_DATA_PATHS.values()
        for candidate in candidates
    )
finally:
    preferences.addons.remove(cache_addon)
    bpy.utils.unregister_class(GestureHelperCachePreferencesB)
    bpy.utils.unregister_class(GestureHelperCacheItem)

# These named collections allow later key collisions, so their elements are
# deliberately unsupported even while their current keys are unique.
marker = scene.timeline_markers.new(
    'Gesture "Helper" Marker',
    frame=scene.frame_start,
)
try:
    assert resolve_context_data_path(marker, "name") is None
    assert not can_use_clipboard_context_fallback(marker)
finally:
    scene.timeline_markers.remove(marker)

original_keying_set_length = len(scene.keying_sets)
keying_set = scene.keying_sets.new(
    idname="GestureHelperPathProbe",
    name='Gesture "Helper" Keying Set',
)
keying_path = keying_set.paths.add(scene, "frame_start")
try:
    assert resolve_context_data_path(keying_set, "bl_label") is None
    assert not can_use_clipboard_context_fallback(keying_set)
    assert resolve_context_data_path(
        keying_path, "use_entire_array",
    ) is None
    assert not can_use_clipboard_context_fallback(keying_path)
finally:
    keying_set.paths.remove(keying_path)
    scene.keying_sets.active_index = len(scene.keying_sets) - 1
    assert bpy.ops.anim.keying_set_remove() == {'FINISHED'}
assert len(scene.keying_sets) == original_keying_set_length

view_layer = bpy.context.view_layer
freestyle_linesets = view_layer.freestyle_settings.linesets
first_lineset = freestyle_linesets.new('Gesture "Helper" Lineset A')
second_lineset = freestyle_linesets.new('Gesture "Helper" Lineset B')
try:
    assert resolve_context_data_path(second_lineset, "show_render") is None
    assert not can_use_clipboard_context_fallback(second_lineset)
    assert resolve_context_data_path(second_lineset.linestyle, "alpha") is None
    assert not can_use_clipboard_context_fallback(second_lineset.linestyle)

    freestyle_linesets.active_index = len(freestyle_linesets) - 2
    assert freestyle_linesets.active.name == first_lineset.name
    assert resolve_context_data_path(second_lineset, "show_render") is None
    assert resolve_context_data_path(second_lineset.linestyle, "alpha") is None
finally:
    freestyle_linesets.remove(second_lineset)
    freestyle_linesets.remove(first_lineset)

freestyle_modules = view_layer.freestyle_settings.modules
freestyle_module = freestyle_modules.new()
try:
    assert resolve_context_data_path(freestyle_module, "use") is None
    assert not can_use_clipboard_context_fallback(freestyle_module)
finally:
    freestyle_modules.remove(freestyle_module)

probe_view_layer = scene.view_layers.new('Gesture "Helper" Path ViewLayer')
bpy.context.window.view_layer = probe_view_layer
try:
    if hasattr(probe_view_layer, "aovs"):
        first_aov = probe_view_layer.aovs.add()
        second_aov = probe_view_layer.aovs.add()
        first_aov.name = 'Gesture "Helper" AOV A'
        second_aov.name = 'Gesture "Helper" AOV B'
        for aov in (first_aov, second_aov):
            assert resolve_context_data_path(aov, "type") is None
            assert not can_use_clipboard_context_fallback(aov)

    if hasattr(probe_view_layer, "lightgroups"):
        first_lightgroup = probe_view_layer.lightgroups.add()
        second_lightgroup = probe_view_layer.lightgroups.add()
        first_lightgroup.name = 'Gesture "Helper" Lightgroup A'
        second_lightgroup.name = 'Gesture "Helper" Lightgroup B'
        for lightgroup in (first_lightgroup, second_lightgroup):
            assert_resolves(
                lightgroup,
                keyed_owner(
                    "bpy.context.view_layer.lightgroups",
                    lightgroup.name,
                ),
                "name",
            )
        first_lightgroup.name = second_lightgroup.name
        assert first_lightgroup.name != second_lightgroup.name
        assert_resolves(
            second_lightgroup,
            keyed_owner(
                "bpy.context.view_layer.lightgroups",
                second_lightgroup.name,
            ),
            "name",
        )
finally:
    bpy.context.window.view_layer = view_layer
    scene.view_layers.remove(probe_view_layer)

# Recursive named collections must not stop at an arbitrary metadata depth.
layer_collections = [
    bpy.data.collections.new(f'Gesture "Helper" Layer {suffix}')
    for suffix in ("A", "B", "C")
]
scene.collection.children.link(layer_collections[0])
layer_collections[0].children.link(layer_collections[1])
layer_collections[1].children.link(layer_collections[2])
try:
    owner_path = "bpy.context.view_layer.layer_collection"
    layer_collection = view_layer.layer_collection
    for collection in layer_collections:
        owner_path += ".children" + keyed_owner("", collection.name)
        layer_collection = layer_collection.children[collection.name]
        assert_resolves(layer_collection, owner_path, "exclude")
finally:
    for collection in reversed(layer_collections):
        bpy.data.collections.remove(collection)

# KeyConfig/KeyMap keys can collide or be replaced, and KeyMapItem only has a
# mutable numeric index. All three levels must fail closed.
keyconfigs = bpy.context.window_manager.keyconfigs
original_keyconfig_length = len(keyconfigs)
keyconfig = keyconfigs.new(name='Gesture "Helper" KeyConfig')
try:
    keyconfig_owner = keyed_owner(
        "bpy.context.window_manager.keyconfigs",
        keyconfig.name,
    )
    assert resolve_context_data_path(keyconfig, "name") is None
    assert not can_use_clipboard_context_fallback(keyconfig)

    unique_keymap = keyconfig.keymaps.new(
        name='Gesture "Helper" Unique KeyMap',
        space_type='EMPTY',
        region_type='WINDOW',
    )
    unique_keymap_owner = keyed_owner(
        f"{keyconfig_owner}.keymaps",
        unique_keymap.name,
    )
    assert resolve_context_data_path(
        unique_keymap, "show_expanded_items",
    ) is None
    assert not can_use_clipboard_context_fallback(unique_keymap)

    duplicate_keymaps = (
        keyconfig.keymaps.new(
            name='Gesture "Helper" Duplicate KeyMap',
            space_type='VIEW_3D',
            region_type='WINDOW',
        ),
        keyconfig.keymaps.new(
            name='Gesture "Helper" Duplicate KeyMap',
            space_type='IMAGE_EDITOR',
            region_type='WINDOW',
        ),
    )
    for duplicate_keymap in duplicate_keymaps:
        assert resolve_context_data_path(
            duplicate_keymap, "show_expanded_items",
        ) is None
        assert not can_use_clipboard_context_fallback(duplicate_keymap)

    keymap_items = [
        unique_keymap.keymap_items.new(
            "wm.search_menu",
            type=key_type,
            value='PRESS',
        )
        for key_type in ("F5", "F6", "F7")
    ]
    for keymap_item in keymap_items:
        assert resolve_context_data_path(keymap_item, "active") is None
        assert not can_use_clipboard_context_fallback(keymap_item)

    unstable_item_path = (
        f"{unique_keymap_owner}.keymap_items[1]"
        .removeprefix("bpy.context.")
    )
    assert pointer_address(
        context_path_resolve(unstable_item_path)
    ) == pointer_address(keymap_items[1])
    unique_keymap.keymap_items.remove(keymap_items[0])
    assert pointer_address(
        context_path_resolve(unstable_item_path)
    ) == pointer_address(keymap_items[2])
finally:
    keyconfigs.remove(keyconfig)
assert len(keyconfigs) == original_keyconfig_length

# Validate every generated candidate that is live in the default context.
validated_candidates = 0
safe_generated_id_types = {
    "Brush",
    "FreestyleLineStyle",
    "Material",
    "Object",
    "Scene",
    "Screen",
    "WindowManager",
    "WorkSpace",
    "World",
}
for identifier, candidates in tuple(CREATE_ELEMENT_DATA_PATHS.items()):
    rna_type = getattr(bpy.types, identifier, None)
    rna = getattr(rna_type, "bl_rna", None)
    if rna is not None and rna_is_a(rna, "ID"):
        assert identifier in safe_generated_id_types, (identifier, candidates)
        if identifier == "Brush":
            assert all(
                candidate.endswith(".brush") for candidate in candidates
            ), candidates
        # Avoid dereferencing nullable ID getters in Blender 4.2. The type and
        # path-shape assertions above still reject nested Library candidates.
        continue
    for candidate in candidates:
        if not candidate.startswith("bpy.context."):
            continue
        try:
            target = context_path_resolve(
                candidate.removeprefix("bpy.context.")
            )
        except PATH_EXCEPTIONS:
            continue
        if target is None or getattr(target, "bl_rna", None) is None:
            continue
        if (
                target.bl_rna.identifier == "ID"
                and rna is not None
                and rna_is_a(rna, "ID")
        ):
            # Blender 4.2 leaves some safe Brush roots as generic ID pointers.
            continue
        if not rna_is_a(target.bl_rna, identifier):
            if (
                    candidate == "bpy.context.space_data"
                    and rna_is_a(target.bl_rna, "Space")
            ):
                # Every concrete Space type shares this semantic context root.
                continue
            raise AssertionError(
                (identifier, candidate, target.bl_rna.identifier)
            )
        prop_identifier = sample_property(target)
        if prop_identifier is None:
            continue
        candidate_data_path = f"{candidate}.{prop_identifier}"
        assert validate_context_data_path(
            target, prop_identifier, candidate_data_path,
        ), (identifier, candidate_data_path)
        try:
            assert_resolves(target, prop_identifier=prop_identifier)
        except AssertionError as exc:
            raise AssertionError(
                (candidate, target.bl_rna.identifier, prop_identifier)
            ) from exc
        validated_candidates += 1
assert validated_candidates >= 35, validated_candidates

# Switch one real area through every editor and validate its root and live children.
window = bpy.context.window
screen = window.screen
area = max(screen.areas, key=lambda item: item.width * item.height)
original_area_type = area.type
validated_spaces = set()
try:
    for enum_item in bpy.types.Area.bl_rna.properties['type'].enum_items:
        try:
            area.type = enum_item.identifier
        except (TypeError, ValueError):
            continue
        region = next(
            (item for item in area.regions if item.type == 'WINDOW'),
            None,
        )
        override = {'window': window, 'screen': screen, 'area': area}
        if region is not None:
            override['region'] = region
        with bpy.context.temp_override(**override):
            space = bpy.context.space_data
            if space is None or space.bl_rna.identifier == "Space":
                continue
            validated_spaces.add(space.bl_rna.identifier)
            assert_resolves(space, "bpy.context.space_data")
            for rna_prop in space.bl_rna.properties:
                if (
                        rna_prop.type != 'POINTER'
                        or rna_prop.identifier in {'rna_type', 'original'}
                        or rna_is_a(rna_prop.fixed_type, "ID")
                ):
                    continue
                try:
                    child = getattr(space, rna_prop.identifier)
                except PATH_EXCEPTIONS:
                    continue
                if child is None or sample_property(child) is None:
                    continue
                assert_resolves(child)

            if area.type == 'TEXT_EDITOR':
                text = bpy.data.texts.new("Gesture Helper Path Text")
                text.write("line")
                space.text = text
                assert_resolves(text, "bpy.context.space_data.text")
                assert_resolves(
                    text.lines[0],
                    "bpy.context.space_data.text.current_line",
                    "body",
                )
finally:
    area.type = original_area_type

assert len(validated_spaces) >= 15, validated_spaces
print(
    "property data paths smoke passed",
    bpy.app.version_string,
    len(CREATE_ELEMENT_DATA_PATHS),
    validated_candidates,
    len(validated_spaces),
    flush=True,
)
