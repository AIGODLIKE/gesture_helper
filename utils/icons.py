import os
import zipfile
from os.path import abspath, basename, join

import bpy
import bpy.utils.previews

icons = None
icons_map = None
icons_path_map: dict[str, str] | None = None
_builtin_icon_names: frozenset[str] | None = None

CUSTOM_ICONS_DIR_NAME = "custom_icons"
CUSTOM_ICONS_EXPORT_FILENAME = "gesture_helper_custom_icons.zip"


def get_custom_icons_folder() -> str:
    """User custom icons folder under extension_path_user (never the install tree)."""
    from .backups import get_extension_user_folder
    return abspath(join(get_extension_user_folder(), CUSTOM_ICONS_DIR_NAME))


def ensure_custom_icons_folder() -> str:
    """Return the custom icons folder, creating it when missing."""
    path = get_custom_icons_folder()
    os.makedirs(path, exist_ok=True)
    return path


def list_custom_icon_pngs() -> list[str]:
    """Return absolute paths of top-level PNG files in the custom icons folder."""
    folder = get_custom_icons_folder()
    if not os.path.isdir(folder):
        return []
    paths = []
    for name in os.listdir(folder):
        if not name.lower().endswith(".png"):
            continue
        path = abspath(join(folder, name))
        if os.path.isfile(path):
            paths.append(path)
    return sorted(paths)


def export_custom_icons_zip(filepath: str) -> int:
    """Write top-level custom PNG icons into a zip archive. Returns file count."""
    pngs = list_custom_icon_pngs()
    if not pngs:
        return 0
    with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in pngs:
            zf.write(path, arcname=basename(path))
    return len(pngs)


def import_custom_icons_zip(filepath: str) -> int:
    """Extract PNG files from a zip into the custom icons folder (overwrite)."""
    folder = ensure_custom_icons_folder()
    imported = 0
    with zipfile.ZipFile(filepath, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = basename(info.filename)
            if not name or not name.lower().endswith(".png"):
                continue
            # Reject path traversal / empty names after basename.
            if name in (".", "..") or os.sep in name or (os.altsep and os.altsep in name):
                continue
            target = join(folder, name)
            with zf.open(info, "r") as src, open(target, "wb") as dst:
                dst.write(src.read())
            imported += 1
    return imported


def normalize_icon_name(icon_name: str) -> str:
    """Strip optional ``.png`` suffix from icon identifiers."""
    if not icon_name:
        return ""
    name = str(icon_name).strip()
    if name.lower().endswith(".png"):
        return name[:-4]
    return name


def get_builtin_icon_names() -> frozenset[str]:
    """Return Blender built-in icon identifiers from the UI layout RNA enum."""
    global _builtin_icon_names
    if _builtin_icon_names is None:
        _builtin_icon_names = frozenset(
            bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()
        )
    return _builtin_icon_names


def is_builtin_icon(icon_name: str) -> bool:
    name = normalize_icon_name(icon_name)
    return bool(name) and name in get_builtin_icon_names()


def has_preview_icon(icon_name: str) -> bool:
    """Return whether a PNG preview path is indexed for GPU / icon_value drawing."""
    name = normalize_icon_name(icon_name).lower()
    if not name:
        return False
    Icons._ensure_registered()
    return name in icons_path_map


def icon_layout_kwargs(icon_name: str) -> dict:
    """Return ``icon`` or ``icon_value`` kwargs for UILayout widgets."""
    name = normalize_icon_name(icon_name)
    if is_builtin_icon(name):
        return {"icon": name}
    preview = ensure_preview_loaded(name)
    if preview is None:
        return {"icon": "ERROR"}
    return {"icon_value": preview.icon_id}


def index_from_folder(icon_folder_path: str, icon_type: str) -> None:
    """Scan a folder for PNGs and record names/paths without loading previews."""
    global icons_map, icons_path_map
    if not os.path.isdir(icon_folder_path):
        return
    for file in os.listdir(icon_folder_path):
        if not file.lower().endswith(".png"):
            continue
        file_path = os.path.abspath(os.path.join(icon_folder_path, file))
        if not os.path.isfile(file_path):
            continue
        name, _suffix = file.split(".", 1)
        key = name.lower()
        if key in icons_path_map:
            continue
        icons_path_map[key] = file_path
        icons_map[icon_type].append(name)


def get_all_icons() -> list[str]:
    global icons_map
    Icons._ensure_registered()
    names = list(get_builtin_icon_names())
    names.extend(icons_map['ADDON'])
    names.extend(icons_map['CUSTOM'])
    return names


def get_blender_icons() -> list[str]:
    return sorted(get_builtin_icon_names())


def check_icon(icon_identifier: str) -> bool:
    name = normalize_icon_name(icon_identifier)
    if not name:
        return False
    if is_builtin_icon(name):
        return True
    Icons._ensure_registered()
    return name.lower() in icons_path_map


def _preview_is_empty(preview) -> bool:
    icon_size = preview.icon_size
    if isinstance(icon_size, int):
        if icon_size <= 0:
            return True
    elif not icon_size or icon_size[0] <= 0 or icon_size[1] <= 0:
        return True
    return not preview.icon_pixels and not preview.icon_pixels_float


def ensure_preview_loaded(key: str):
    """Load a single PNG into the preview collection on first use.

    Returns the preview, or None when the key is unknown / still empty after retry.
    """
    global icons, icons_path_map
    Icons._ensure_registered()
    lookup = normalize_icon_name(key).lower()
    if not lookup:
        return None

    path = icons_path_map.get(lookup)
    if path is None:
        return None

    try:
        preview = icons[lookup]
    except KeyError:
        preview = icons.load(lookup, path, 'IMAGE', force_reload=True)

    if _preview_is_empty(preview):
        preview = icons.load(lookup, path, 'IMAGE', force_reload=True)
        if _preview_is_empty(preview):
            return None
    return preview


class Icons:

    @staticmethod
    def register():
        global icons, icons_map, icons_path_map
        if icons is not None:
            return
        icons = bpy.utils.previews.new()
        icons_map = {"ADDON": [], "CUSTOM": []}
        icons_path_map = {}
        from ..utils.public import ADDON_FOLDER

        icon_root = os.path.join(ADDON_FOLDER, 'src', 'icon')
        index_from_folder(icon_root, "ADDON")
        index_from_folder(os.path.join(icon_root, 'blender'), "ADDON")
        index_from_folder(get_custom_icons_folder(), "CUSTOM")

    @staticmethod
    def _ensure_registered() -> None:
        if icons is None:
            Icons.register()

    @staticmethod
    def get(key):
        """Return preview icon; prefers loaded PNG even when name matches a built-in."""
        preview = ensure_preview_loaded(key)
        if preview is None:
            raise KeyError(f"No preview icon for {key!r}")
        return preview

    @staticmethod
    def unregister() -> None:
        global icons, icons_map, icons_path_map, _builtin_icon_names
        if icons:
            bpy.utils.previews.remove(icons)

        icons = None
        icons_map = None
        icons_path_map = None
        _builtin_icon_names = None
        from .texture import Texture
        Texture.clear()

    @staticmethod
    def reload_icons() -> None:
        Icons.unregister()
        Icons.register()
