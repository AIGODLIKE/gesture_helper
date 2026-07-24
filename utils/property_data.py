import ast
from collections import defaultdict

import bpy


_RNA_PATH_EXCEPTIONS = (
    AttributeError,
    IndexError,
    KeyError,
    OverflowError,
    ReferenceError,
    RuntimeError,
    SystemError,
    TypeError,
    ValueError,
)


# These collection/context aliases cannot be inferred from POINTER properties.
_CREATE_ELEMENT_PATH_SEEDS = {
    "GPencilLayer": (
        "bpy.context.active_annotation_layer",
        "bpy.context.active_gpencil_layer",
    ),
    "AnnotationLayer": ("bpy.context.active_annotation_layer",),
    "ThemeUserInterface": (
        "bpy.context.preferences.themes[0].user_interface",
    ),
    "MaskLayer": ("bpy.context.space_data.mask.layers.active",),
    "MaskSpline": (
        "bpy.context.space_data.mask.layers.active.splines.active",
    ),
    "MaskSplinePoint": (
        "bpy.context.space_data.mask.layers.active.splines.active_point",
    ),
    "TextLine": (
        "bpy.context.space_data.text.current_line",
        "bpy.context.space_data.text.select_end_line",
    ),
}

# Short semantic roots remain stable when screen layout indices change.
_CREATE_ELEMENT_RNA_ROOTS = (
    ("ToolSettings", "bpy.context.tool_settings", 4),
    ("Preferences", "bpy.context.preferences", 4),
    ("Theme", "bpy.context.preferences.themes[0]", 4),
    ("ThemeStyle", "bpy.context.preferences.ui_styles[0]", 3),
    ("ViewLayer", "bpy.context.view_layer", 3),
    ("Scene", "bpy.context.scene", 3),
    ("Object", "bpy.context.object", 3),
    ("World", "bpy.context.scene.world", 2),
    ("Material", "bpy.context.object.active_material", 2),
    ("Screen", "bpy.context.screen", 2),
    ("WorkSpace", "bpy.context.workspace", 2),
    ("WindowManager", "bpy.context.window_manager", 4),
    ("Area", "bpy.context.area", 2),
    ("Region", "bpy.context.region", 2),
)

_CREATE_ELEMENT_INDEXED_COLLECTIONS = (
    (
        "TransformOrientationSlot",
        "bpy.context.scene.transform_orientation_slots",
    ),
    (
        "ThemeBoneColorSet",
        "bpy.context.preferences.themes[0].bone_color_sets",
    ),
    (
        "ThemeCollectionColor",
        "bpy.context.preferences.themes[0].collection_color",
    ),
    (
        "ThemeStripColor",
        "bpy.context.preferences.themes[0].strip_color",
    ),
    (
        "UserSolidLight",
        "bpy.context.preferences.system.solid_lights",
    ),
)

_LIVE_PATH_POINTER = 'POINTER'
_LIVE_PATH_COLLECTION = 'COLLECTION'
_LIVE_PATH_RECURSIVE_COLLECTION = 'RECURSIVE_COLLECTION'
_STATIC_COLLECTION_IDENTIFIERS = frozenset(
    identifier
    for identifier, _collection_path in _CREATE_ELEMENT_INDEXED_COLLECTIONS
) | {"Theme", "ThemeStyle"}
_CREATE_ELEMENT_LIVE_PATH_RECIPES = {}
_UNSAFE_LIVE_PATH_IDENTIFIERS = frozenset({
    # Their only RNA path is a mutable numeric index. Persisting it can silently
    # redirect a gesture after an earlier collection item is removed.
    "ColorRampElement",
    "FreestyleModuleSettings",
    "KeyMapItem",
})
_RUNTIME_INDEXED_COLLECTION_PATHS = {
    "RegionView3D": (
        "bpy.context.space_data.region_quadviews",
    ),
}
_STABLE_LIVE_KEY_IDENTIFIERS = frozenset({
    # Blender preserves the original target's key when these names collide.
    "LayerCollection",
    "Lightgroup",
    "ViewLayer",
})
_SAFE_SEMANTIC_CONTEXT_IDENTIFIERS = frozenset({
    # This is a selected resource alias, not a persisted collection identity.
    "StudioLight",
})

_RNA_POINTER_SKIP = frozenset({
    "rna_type",
    "original",
    "depsgraph",
    # Blender 4.3 can crash natively when this getter has no active brush.
    "eraser_brush",
})
_RNA_CONTEXT_ID_TYPES = frozenset({"Brush"})
_RNA_EXPAND_ID_TYPES = frozenset()
_RNA_LIVE_ID_TYPES = frozenset({"FreestyleLineStyle"})

_SAFE_ID_CONTEXT_PATHS = (
    "bpy.context.object.data",
    "bpy.context.object.active_material",
    "bpy.context.scene.world",
    "bpy.context.scene",
    "bpy.context.screen",
    "bpy.context.workspace",
    "bpy.context.window_manager",
    "bpy.context.space_data.text",
    "bpy.context.space_data.image",
    "bpy.context.space_data.clip",
    "bpy.context.space_data.mask",
    "bpy.context.space_data.node_tree",
    "bpy.context.space_data.edit_tree",
    "bpy.context.space_data.id",
    "bpy.context.space_data.id_from",
    "bpy.context.space_data.pin_id",
)


def _rna_is_a(rna, identifier: str) -> bool:
    while rna is not None:
        if rna.identifier == identifier:
            return True
        rna = rna.base
    return False


def _has_numeric_rna_path_index(path: str) -> bool:
    """Return whether a valid RNA path contains an integer subscript."""
    if not path:
        return False
    separator = "" if path.lstrip().startswith("[") else "."
    try:
        expression = ast.parse(
            f"_rna_root{separator}{path}", mode="eval",
        )
    except SyntaxError:
        return False
    for node in ast.walk(expression):
        if not isinstance(node, ast.Subscript):
            continue
        index = node.slice
        if isinstance(index, ast.Constant) and type(index.value) is int:
            return True
        if (
                isinstance(index, ast.UnaryOp)
                and isinstance(index.op, (ast.USub, ast.UAdd))
                and isinstance(index.operand, ast.Constant)
                and type(index.operand.value) is int
        ):
            return True
    return False


def _add_candidate_path(paths, identifier: str, path: str) -> None:
    if identifier and path not in paths[identifier]:
        paths[identifier].append(path)


def _add_live_path_recipe(
        recipes, identifier: str, root_path: str,
        steps: tuple[tuple[str, str], ...]) -> None:
    if identifier in _STATIC_COLLECTION_IDENTIFIERS:
        return
    recipe = (root_path, steps)
    if identifier and recipe not in recipes[identifier]:
        recipes[identifier].append(recipe)


def _identifier_prefers_live_path(identifier: str) -> bool:
    """Prefer keyed recipes for collection members over active aliases."""
    if identifier not in (
            _STABLE_LIVE_KEY_IDENTIFIERS
            | _RUNTIME_INDEXED_COLLECTION_PATHS.keys()
    ):
        return False
    return _identifier_has_collection_recipe(identifier)


def _identifier_has_collection_recipe(identifier: str) -> bool:
    return any(
        steps
        and steps[-1][1] in {
            _LIVE_PATH_COLLECTION,
            _LIVE_PATH_RECURSIVE_COLLECTION,
        }
        for _root_path, steps in _CREATE_ELEMENT_LIVE_PATH_RECIPES.get(
            identifier, (),
        )
    )


def _identifier_has_unstable_collection_path(identifier: str) -> bool:
    return (
        _identifier_has_collection_recipe(identifier)
        and identifier not in (
            _STABLE_LIVE_KEY_IDENTIFIERS
            | _RUNTIME_INDEXED_COLLECTION_PATHS.keys()
        )
    )


def _collect_rna_pointer_paths(
        paths, rna, base_path: str, depth: int,
        ancestry: frozenset[str] = frozenset()) -> None:
    """Collect bounded POINTER paths without walking fragile live RNA data."""
    _add_candidate_path(paths, rna.identifier, base_path)
    if depth <= 0 or rna.identifier in ancestry:
        return
    ancestry = ancestry | {rna.identifier}

    for prop in rna.properties:
        if prop.type != 'POINTER' or prop.identifier in _RNA_POINTER_SKIP:
            continue
        child_rna = prop.fixed_type
        if child_rna is None:
            continue
        child_path = f"{base_path}.{prop.identifier}"
        child_is_id = _rna_is_a(child_rna, "ID")
        if child_is_id:
            if child_rna.identifier not in _RNA_CONTEXT_ID_TYPES:
                continue
            _add_candidate_path(paths, child_rna.identifier, child_path)
            if child_rna.identifier not in _RNA_EXPAND_ID_TYPES:
                continue
        elif child_rna.identifier not in {"ID", "Struct"}:
            _add_candidate_path(paths, child_rna.identifier, child_path)
        _collect_rna_pointer_paths(
            paths, child_rna, child_path, depth - 1, ancestry,
        )


def _collect_rna_live_path_recipes(
        recipes, rna, root_path: str, depth: int,
        steps: tuple[tuple[str, str], ...] = (),
        ancestry: frozenset[str] = frozenset(),
        crossed_collection: bool = False) -> None:
    """Describe collection-owned RNA paths without touching live getters."""
    if depth <= 0 or rna.identifier in ancestry:
        return
    ancestry = ancestry | {rna.identifier}

    for prop in rna.properties:
        if prop.identifier in _RNA_POINTER_SKIP:
            continue
        if prop.type not in {_LIVE_PATH_POINTER, _LIVE_PATH_COLLECTION}:
            continue
        child_rna = prop.fixed_type
        if (
                child_rna is None
                or child_rna.identifier in {"ID", "Struct"}
                or child_rna.identifier in _UNSAFE_LIVE_PATH_IDENTIFIERS
        ):
            continue

        is_collection = prop.type == _LIVE_PATH_COLLECTION
        child_is_id = _rna_is_a(child_rna, "ID")
        if is_collection and child_is_id:
            continue
        if (
                not is_collection
                and child_is_id
                and child_rna.identifier not in (
                    _RNA_CONTEXT_ID_TYPES | _RNA_LIVE_ID_TYPES
                )
        ):
            continue

        step_type = prop.type
        if is_collection and child_rna.identifier == rna.identifier:
            step_type = _LIVE_PATH_RECURSIVE_COLLECTION
        child_steps = steps + ((prop.identifier, step_type),)
        child_crossed_collection = crossed_collection or is_collection
        if child_crossed_collection:
            _add_live_path_recipe(
                recipes, child_rna.identifier, root_path, child_steps,
            )
        if step_type == _LIVE_PATH_RECURSIVE_COLLECTION or (
                child_is_id
                and child_rna.identifier not in _RNA_EXPAND_ID_TYPES
        ):
            continue
        _collect_rna_live_path_recipes(
            recipes,
            child_rna,
            root_path,
            depth - 1,
            child_steps,
            ancestry,
            child_crossed_collection,
        )


def _collect_live_addon_preference_paths(paths, recipes) -> None:
    """Include concrete add-on preference classes registered at runtime."""
    try:
        addons = bpy.context.preferences.addons
    except _RNA_PATH_EXCEPTIONS:
        return

    try:
        for addon in addons:
            try:
                module = addon.module
                preferences = addon.preferences
            except _RNA_PATH_EXCEPTIONS:
                continue
            rna = getattr(preferences, "bl_rna", None)
            if not module or rna is None:
                continue
            escaped_module = bpy.utils.escape_identifier(module)
            base_path = (
                "bpy.context.preferences.addons"
                f'["{escaped_module}"].preferences'
            )
            _collect_rna_pointer_paths(paths, rna, base_path, 4)
            _collect_rna_live_path_recipes(
                recipes,
                rna,
                base_path,
                4,
            )
    except _RNA_PATH_EXCEPTIONS:
        return


def _build_create_element_data_paths():
    """Build version-aware RNA candidates for context-menu properties."""
    paths = defaultdict(list)
    recipes = defaultdict(list)
    for identifier, candidates in _CREATE_ELEMENT_PATH_SEEDS.items():
        for path in candidates:
            _add_candidate_path(paths, identifier, path)

    for type_name, base_path, depth in _CREATE_ELEMENT_RNA_ROOTS:
        rna_type = getattr(bpy.types, type_name, None)
        rna = getattr(rna_type, "bl_rna", None)
        if rna is not None:
            _collect_rna_pointer_paths(paths, rna, base_path, depth)
            _collect_rna_live_path_recipes(
                recipes,
                rna,
                base_path,
                depth,
            )

    for identifier, collection_path in _CREATE_ELEMENT_INDEXED_COLLECTIONS:
        try:
            collection = bpy.types.Context.path_resolve(
                bpy.context,
                collection_path.removeprefix("bpy.context."),
            )
            length = len(collection)
        except _RNA_PATH_EXCEPTIONS:
            length = 0
        for index in range(length):
            _add_candidate_path(
                paths, identifier, f"{collection_path}[{index}]",
            )

    _collect_live_addon_preference_paths(paths, recipes)

    for type_name in dir(bpy.types):
        if not type_name.startswith("Space"):
            continue
        rna_type = getattr(bpy.types, type_name, None)
        rna = getattr(rna_type, "bl_rna", None)
        if (
                rna is None
                or rna.identifier == "Space"
                or not _rna_is_a(rna, "Space")
        ):
            continue
        _collect_rna_pointer_paths(
            paths, rna, "bpy.context.space_data", 3,
        )
        _collect_rna_live_path_recipes(
            recipes,
            rna,
            "bpy.context.space_data",
            3,
        )

    return (
        {
            identifier: tuple(candidates)
            for identifier, candidates in paths.items()
        },
        {
            identifier: tuple(identifier_recipes)
            for identifier, identifier_recipes in recipes.items()
        },
    )


# One RNA type can have several live owners. Callers must identity-check a
# candidate before using it; choosing only by class name is not valid.
(
    CREATE_ELEMENT_DATA_PATHS,
    _CREATE_ELEMENT_LIVE_PATH_RECIPES,
) = _build_create_element_data_paths()
_LIVE_CREATE_ELEMENT_DATA_PATHS = {}
_CONFIRMED_UNSTABLE_PATHS = set()


def _rebuild_create_element_data_paths() -> None:
    """Synchronize static paths and recipes after runtime RNA registration."""
    rebuilt_paths, rebuilt_recipes = _build_create_element_data_paths()
    CREATE_ELEMENT_DATA_PATHS.clear()
    CREATE_ELEMENT_DATA_PATHS.update(rebuilt_paths)
    _CREATE_ELEMENT_LIVE_PATH_RECIPES.clear()
    _CREATE_ELEMENT_LIVE_PATH_RECIPES.update(rebuilt_recipes)
    _LIVE_CREATE_ELEMENT_DATA_PATHS.clear()

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
    "VERTEX_GREASE_PENCIL": 'bpy.context.tool_settings.gpencil_vertex_paint',
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
        try:
            id_data = (
                getattr(pointer, 'id_data', None)
                if pointer is not None else None
            )
        except _RNA_PATH_EXCEPTIONS:
            id_data = None
        if isinstance(id_data, bpy.types.Object) and id_data.name == name and obj == id_data:
            return f"bpy.context.object.{rest}"
        return None

    if text.startswith('bpy.data.'):
        return None
    return normalize_context_data_path(text)


_DIRECT_CONTEXT_PRIORITY = (
    "object",
    "active_object",
    "edit_object",
    "pose_object",
    "scene",
    "view_layer",
    "space_data",
    "tool_settings",
    "region_data",
    "area",
    "region",
    "screen",
    "workspace",
    "preferences",
    "window_manager",
    "window",
    "collection",
    "layer_collection",
)

_TRANSIENT_CONTEXT_MEMBERS = frozenset({
    "active_operator",
    "button_operator",
    "button_pointer",
    "button_prop",
    "gizmo_group",
    "property",
    "region_popup",
    "ui_list",
})


def _same_rna_pointer(left, right) -> bool:
    if left is None or right is None:
        return False

    try:
        left_rna = getattr(left, "bl_rna", None)
        right_rna = getattr(right, "bl_rna", None)
    except _RNA_PATH_EXCEPTIONS:
        return False
    if left_rna is None or right_rna is None:
        return False
    if left is right:
        return True
    if not (
            left_rna.identifier != "Struct"
            and right_rna.identifier != "Struct"
            and (
                _rna_is_a(left_rna, right_rna.identifier)
                or _rna_is_a(right_rna, left_rna.identifier)
            )
    ):
        return False

    try:
        left_address = left.as_pointer()
        right_address = right.as_pointer()
        if left_address and right_address:
            return left_address == right_address
    except _RNA_PATH_EXCEPTIONS:
        pass
    try:
        return bool(left == right)
    except _RNA_PATH_EXCEPTIONS:
        return False


def _context_path_target(path: str):
    if not path.startswith("bpy.context."):
        return None
    relative_path = path.removeprefix("bpy.context.")
    try:
        return bpy.types.Context.path_resolve(bpy.context, relative_path)
    except _RNA_PATH_EXCEPTIONS:
        return None


def _pointer_rna_identifiers(pointer) -> tuple[str, ...]:
    identifiers = []
    try:
        rna = getattr(pointer, "bl_rna", None)
        if rna is None:
            return ()
        class_name = pointer.__class__.__name__ if pointer is not None else ""
        while rna is not None:
            identifier = getattr(rna, "identifier", "")
            if (
                    identifier
                    and identifier not in {"ID", "Struct"}
                    and identifier not in identifiers
            ):
                identifiers.append(identifier)
            rna = getattr(rna, "base", None)
    except _RNA_PATH_EXCEPTIONS:
        return ()
    if (
            class_name not in {"ID", "Struct"}
            and class_name
            and class_name not in identifiers
    ):
        identifiers.append(class_name)
    return tuple(identifiers)


def _unstable_path_cache_key(pointer, identifiers):
    try:
        address = pointer.as_pointer()
    except _RNA_PATH_EXCEPTIONS:
        address = id(pointer)
    try:
        relative_path = pointer.path_from_id() or ""
    except _RNA_PATH_EXCEPTIONS:
        relative_path = ""
    try:
        addon_modules = tuple(
            addon.module for addon in bpy.context.preferences.addons
        )
    except _RNA_PATH_EXCEPTIONS:
        addon_modules = ()
    return identifiers, address, relative_path, addon_modules


def _has_confirmed_unstable_collection_path(pointer, identifiers) -> bool:
    if not any(
            _identifier_has_unstable_collection_path(identifier)
            for identifier in identifiers
    ):
        return False

    cache_key = _unstable_path_cache_key(pointer, identifiers)
    if cache_key in _CONFIRMED_UNSTABLE_PATHS:
        return True

    _rebuild_create_element_data_paths()
    if not any(
            _identifier_has_unstable_collection_path(identifier)
            for identifier in identifiers
    ):
        return False
    if len(_CONFIRMED_UNSTABLE_PATHS) >= 256:
        _CONFIRMED_UNSTABLE_PATHS.clear()
    _CONFIRMED_UNSTABLE_PATHS.add(
        _unstable_path_cache_key(pointer, identifiers),
    )
    return True


def can_use_clipboard_context_fallback(pointer) -> bool:
    """Reject clipboard paths when a collection owner lacked a stable key."""
    identifiers = _pointer_rna_identifiers(pointer)
    if not identifiers:
        return False
    collection_identifiers = (
        _UNSAFE_LIVE_PATH_IDENTIFIERS
        | _RUNTIME_INDEXED_COLLECTION_PATHS.keys()
        | _CREATE_ELEMENT_LIVE_PATH_RECIPES.keys()
    )
    if any(
            identifier in collection_identifiers
            for identifier in identifiers
    ):
        return False
    try:
        relative_path = pointer.path_from_id() or ""
    except _RNA_PATH_EXCEPTIONS:
        relative_path = ""
    return not _has_numeric_rna_path_index(relative_path)


def _iter_unique_collection_members(collection_path: str, collection):
    """Yield only collection members with an unambiguous string-key path."""
    try:
        keys = tuple(str(key) for key in collection.keys())
    except _RNA_PATH_EXCEPTIONS:
        return

    key_counts = defaultdict(int)
    for key in keys:
        if key:
            key_counts[key] += 1

    try:
        for index, item in enumerate(collection):
            if index >= len(keys):
                break
            item_rna = getattr(item, "bl_rna", None)
            item_identifier = getattr(item_rna, "identifier", "")
            if item_identifier not in _STABLE_LIVE_KEY_IDENTIFIERS:
                # Most RNA collection names have no persistent identity
                # contract; another item can later take this key.
                continue
            key = keys[index]
            if not key or key_counts[key] != 1:
                continue
            try:
                keyed_item = collection.get(key)
            except _RNA_PATH_EXCEPTIONS:
                continue
            if not _same_rna_pointer(keyed_item, item):
                continue
            escaped_key = bpy.utils.escape_identifier(key)
            yield f'{collection_path}["{escaped_key}"]', item
    except _RNA_PATH_EXCEPTIONS:
        return


def _iter_live_recipe_targets(
        owner_path: str, owner, steps: tuple[tuple[str, str], ...],
        step_index: int = 0,
        visited: frozenset[tuple[str, int]] = frozenset()):
    if step_index >= len(steps):
        yield owner_path, owner
        return

    prop_identifier, prop_type = steps[step_index]
    try:
        value = getattr(owner, prop_identifier)
    except _RNA_PATH_EXCEPTIONS:
        return
    if value is None:
        return

    value_path = f"{owner_path}.{prop_identifier}"
    if prop_type in {
            _LIVE_PATH_COLLECTION,
            _LIVE_PATH_RECURSIVE_COLLECTION,
    }:
        for item_path, item in _iter_unique_collection_members(
                value_path, value):
            try:
                item_address = item.as_pointer()
            except _RNA_PATH_EXCEPTIONS:
                item_address = id(item)
            item_rna = getattr(item, "bl_rna", None)
            item_key = (
                getattr(item_rna, "identifier", ""),
                item_address,
            )
            if item_key in visited:
                continue
            item_visited = visited | {item_key}
            yield from _iter_live_recipe_targets(
                item_path,
                item,
                steps,
                step_index + 1,
                item_visited,
            )
            if prop_type == _LIVE_PATH_RECURSIVE_COLLECTION:
                yield from _iter_live_recipe_targets(
                    item_path,
                    item,
                    steps,
                    step_index,
                    item_visited,
                )
        return

    yield from _iter_live_recipe_targets(
        value_path, value, steps, step_index + 1, visited,
    )


def _refresh_live_candidate_paths(pointer, identifier: str) -> None:
    recipes = _CREATE_ELEMENT_LIVE_PATH_RECIPES.get(identifier, ())
    if not recipes:
        return

    previous_live = _LIVE_CREATE_ELEMENT_DATA_PATHS.get(identifier, ())
    candidates = [
        path
        for path in CREATE_ELEMENT_DATA_PATHS.get(identifier, ())
        if path not in previous_live
    ]
    live_candidates = []
    for root_path, steps in recipes:
        root = _context_path_target(root_path)
        if root is None:
            continue
        for candidate, target in _iter_live_recipe_targets(
                root_path, root, steps):
            if _same_rna_pointer(target, pointer):
                if candidate not in live_candidates:
                    live_candidates.append(candidate)
                break

    CREATE_ELEMENT_DATA_PATHS[identifier] = tuple(
        live_candidates + [
            candidate
            for candidate in candidates
            if candidate not in live_candidates
        ]
    )
    _LIVE_CREATE_ELEMENT_DATA_PATHS[identifier] = tuple(live_candidates)


def _refresh_indexed_live_candidate_paths(identifier: str) -> None:
    previous_live = _LIVE_CREATE_ELEMENT_DATA_PATHS.get(identifier, ())
    candidates = [
        path
        for path in CREATE_ELEMENT_DATA_PATHS.get(identifier, ())
        if path not in previous_live
    ]
    live_candidates = []
    for collection_path in _RUNTIME_INDEXED_COLLECTION_PATHS[identifier]:
        collection = _context_path_target(collection_path)
        if collection is None:
            continue
        try:
            collection_length = len(collection)
        except _RNA_PATH_EXCEPTIONS:
            continue
        live_candidates.extend(
            f"{collection_path}[{index}]"
            for index in range(collection_length)
        )

    for candidate in live_candidates:
        if candidate not in candidates:
            candidates.append(candidate)
    CREATE_ELEMENT_DATA_PATHS[identifier] = tuple(candidates)
    _LIVE_CREATE_ELEMENT_DATA_PATHS[identifier] = tuple(live_candidates)


def _candidate_context_paths(
        pointer, *, refresh_live: bool = True) -> tuple[str, ...]:
    identifiers = _pointer_rna_identifiers(pointer)

    if refresh_live:
        for identifier in identifiers:
            if identifier in _RUNTIME_INDEXED_COLLECTION_PATHS:
                _refresh_indexed_live_candidate_paths(identifier)
            else:
                _refresh_live_candidate_paths(pointer, identifier)

    candidates = []
    for identifier in identifiers:
        if (
                not refresh_live
                and _identifier_prefers_live_path(identifier)
        ):
            continue
        live_paths = _LIVE_CREATE_ELEMENT_DATA_PATHS.get(identifier, ())
        for path in CREATE_ELEMENT_DATA_PATHS.get(identifier, ()):
            if not refresh_live and path in live_paths:
                continue
            if path not in candidates:
                candidates.append(path)
    return tuple(candidates)


def _resolve_candidate_pointer_path(
        pointer, *, refresh_live: bool = True,
        rebuild_on_miss: bool = False) -> str | None:
    for path in _candidate_context_paths(
            pointer, refresh_live=refresh_live):
        if _same_rna_pointer(_context_path_target(path), pointer):
            return path
    if rebuild_on_miss:
        _rebuild_create_element_data_paths()
        for path in _candidate_context_paths(
                pointer, refresh_live=refresh_live):
            if _same_rna_pointer(_context_path_target(path), pointer):
                return path
    return None


def _iter_direct_context_paths():
    try:
        context_items = bpy.context.copy()
    except _RNA_PATH_EXCEPTIONS:
        context_items = {}

    names = list(_DIRECT_CONTEXT_PRIORITY)
    for name in sorted(context_items):
        if name not in names:
            names.append(name)

    for name in names:
        if name in _TRANSIENT_CONTEXT_MEMBERS or not name.isidentifier():
            continue
        try:
            if name in context_items:
                value = context_items[name]
            else:
                value = getattr(bpy.context, name, None)
        except _RNA_PATH_EXCEPTIONS:
            continue
        if value is not None and getattr(value, "bl_rna", None) is not None:
            yield f"bpy.context.{name}", value


def _resolve_direct_context_pointer_path(pointer) -> str | None:
    for path, value in _iter_direct_context_paths():
        if _same_rna_pointer(value, pointer):
            return path
    return None


def _resolve_safe_id_pointer_path(pointer) -> str | None:
    try:
        rna = getattr(pointer, "bl_rna", None)
    except _RNA_PATH_EXCEPTIONS:
        return None
    if rna is None or not _rna_is_a(rna, "ID"):
        return None
    for path in _SAFE_ID_CONTEXT_PATHS:
        if _same_rna_pointer(_context_path_target(path), pointer):
            return path
    return None


def validate_context_data_path(
        pointer, prop_identifier: str, data_path: str) -> bool:
    """Verify that a path's owner is the exact live button pointer."""
    if not data_path or not data_path.startswith("bpy.context."):
        return False
    relative_path = data_path.removeprefix("bpy.context.")
    owner_path, separator, leaf = relative_path.rpartition(".")
    if not separator or leaf != prop_identifier:
        return False
    try:
        owner = bpy.types.Context.path_resolve(bpy.context, owner_path)
        rna_prop = owner.bl_rna.properties.get(prop_identifier)
    except _RNA_PATH_EXCEPTIONS:
        return False
    return rna_prop is not None and _same_rna_pointer(owner, pointer)


def _validated_data_path(
        pointer, prop_identifier: str, owner_path: str | None) -> str | None:
    if not owner_path:
        return None
    data_path = f"{owner_path}.{prop_identifier}"
    if validate_context_data_path(pointer, prop_identifier, data_path):
        return data_path
    return None


def resolve_id_data_context_path(pointer, prop_identifier: str) -> str | None:
    """Resolve a nested RNA pointer through a verified context ID anchor."""
    if pointer is None:
        return None

    identifiers = _pointer_rna_identifiers(pointer)
    if not identifiers:
        return None
    if any(
            identifier in _UNSAFE_LIVE_PATH_IDENTIFIERS
            for identifier in identifiers
    ):
        return None
    if _has_confirmed_unstable_collection_path(pointer, identifiers):
        return None
    try:
        id_data = pointer.id_data
    except _RNA_PATH_EXCEPTIONS:
        return None
    if id_data is None:
        return None

    pointer_is_id = _same_rna_pointer(pointer, id_data)
    if pointer_is_id:
        relative_path = ""
    else:
        try:
            relative_path = pointer.path_from_id() or ""
        except _RNA_PATH_EXCEPTIONS:
            return None
        if not relative_path:
            return None
        if _has_numeric_rna_path_index(relative_path):
            # A mutable CollectionProperty index may silently target another
            # item after insertion/removal. Fixed collections and unique string
            # keys are resolved before this fallback is attempted.
            return None

    anchor = (
        _resolve_direct_context_pointer_path(id_data)
        or _resolve_candidate_pointer_path(id_data, refresh_live=False)
        or _resolve_safe_id_pointer_path(id_data)
    )
    if not anchor:
        return None
    owner_path = (
        f"{anchor}.{relative_path}" if relative_path else anchor
    )
    return _validated_data_path(pointer, prop_identifier, owner_path)


def resolve_view_layer_data_path(pointer, prop_identifier: str) -> str | None:
    """Map a ViewLayer pointer to bpy.context.view_layer or a named layer path."""
    if not isinstance(pointer, bpy.types.ViewLayer):
        return None
    context = bpy.context
    active = context.view_layer
    if _same_rna_pointer(pointer, active):
        return _validated_data_path(
            pointer, prop_identifier, "bpy.context.view_layer",
        )
    scene = context.scene
    if scene is None:
        return None
    for view_layer in scene.view_layers:
        if _same_rna_pointer(view_layer, pointer):
            name = bpy.utils.escape_identifier(view_layer.name)
            return _validated_data_path(
                pointer,
                prop_identifier,
                f'bpy.context.scene.view_layers["{name}"]',
            )
    return None


def resolve_context_data_path(pointer, prop_identifier: str) -> str | None:
    """Map a live RNA pointer to bpy.context.* when it matches current context."""
    if pointer is None or not prop_identifier:
        return None

    identifiers = _pointer_rna_identifiers(pointer)
    if not identifiers:
        return None
    if any(
            identifier in _UNSAFE_LIVE_PATH_IDENTIFIERS
            for identifier in identifiers
    ):
        return None
    view_layer_path = resolve_view_layer_data_path(pointer, prop_identifier)
    if view_layer_path:
        return view_layer_path

    if any(
            _identifier_has_unstable_collection_path(identifier)
            for identifier in identifiers
    ):
        semantic_owner_path = None
        if any(
                identifier in _SAFE_SEMANTIC_CONTEXT_IDENTIFIERS
                for identifier in identifiers
        ):
            semantic_owner_path = _resolve_candidate_pointer_path(
                pointer, refresh_live=False,
            )
        direct_data_path = _validated_data_path(
            pointer,
            prop_identifier,
            semantic_owner_path or _resolve_direct_context_pointer_path(
                pointer,
            ),
        )
        if direct_data_path:
            return direct_data_path
        if _has_confirmed_unstable_collection_path(pointer, identifiers):
            return None

    prefers_live_path = any(
        _identifier_prefers_live_path(identifier)
        for identifier in identifiers
    )

    for owner_path in (
            _resolve_candidate_pointer_path(pointer, refresh_live=False),
            _resolve_safe_id_pointer_path(pointer),
            None if prefers_live_path else _resolve_direct_context_pointer_path(
                pointer,
            ),
    ):
        data_path = _validated_data_path(
            pointer, prop_identifier, owner_path,
        )
        if data_path:
            return data_path

    uses_runtime_index = any(
        identifier in _RUNTIME_INDEXED_COLLECTION_PATHS
        for identifier in identifiers
    )
    if uses_runtime_index:
        data_path = _validated_data_path(
            pointer,
            prop_identifier,
            _resolve_candidate_pointer_path(pointer),
        )
        if data_path:
            return data_path

    if not uses_runtime_index:
        data_path = _validated_data_path(
            pointer,
            prop_identifier,
            _resolve_candidate_pointer_path(
                pointer,
                rebuild_on_miss=True,
            ),
        )
        if data_path:
            return data_path

    id_data_path = resolve_id_data_context_path(pointer, prop_identifier)
    if id_data_path:
        return id_data_path

    return _validated_data_path(
        pointer,
        prop_identifier,
        _resolve_safe_id_pointer_path(pointer),
    )
