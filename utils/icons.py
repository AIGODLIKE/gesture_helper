import os

import bpy
import bpy.utils.previews

icons = None
icons_map = None
_builtin_icon_names: frozenset[str] | None = None


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
    """Return whether a PNG preview is loaded for GPU / icon_value drawing."""
    name = normalize_icon_name(icon_name).lower()
    if not name:
        return False
    Icons._ensure_registered()
    return name in icons


def icon_layout_kwargs(icon_name: str) -> dict:
    """Return ``icon`` or ``icon_value`` kwargs for UILayout widgets."""
    name = normalize_icon_name(icon_name)
    if is_builtin_icon(name):
        return {"icon": name}
    Icons._ensure_registered()
    try:
        return {"icon_value": icons[name.lower()].icon_id}
    except KeyError:
        return {"icon": "ERROR"}


def load_from_folder(icon_folder_path: str, icon_type: str) -> None:
    global icons_map
    if not os.path.isdir(icon_folder_path):
        return
    for file in os.listdir(icon_folder_path):
        is_png = file.lower().endswith('.png')
        file_path = os.path.abspath(os.path.join(icon_folder_path, file))
        if is_png and os.path.isfile(file_path):
            name, _suffix = file.split('.', 1)
            key = name.lower()
            if key in icons:
                continue
            icons.load(key, file_path, 'IMAGE', force_reload=True)
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
    return name.lower() in icons


def _preview_is_empty(preview) -> bool:
    icon_size = preview.icon_size
    if isinstance(icon_size, int):
        if icon_size <= 0:
            return True
    elif not icon_size or icon_size[0] <= 0 or icon_size[1] <= 0:
        return True
    return not preview.icon_pixels and not preview.icon_pixels_float


def has_empty_icons() -> bool:
    """Return True when add-on preview icons are missing or contain no pixel data."""
    global icons, icons_map
    if icons is None or not icons_map:
        return True
    for icon_type in ("ADDON", "CUSTOM"):
        for name in icons_map[icon_type]:
            try:
                preview = icons[name.lower()]
            except KeyError:
                return True
            if _preview_is_empty(preview):
                return True
    return False


def ensure_icons_loaded() -> bool:
    """Reload add-on preview icons when startup left any entries empty."""
    if not has_empty_icons():
        return False
    Icons.reload_icons()
    return has_empty_icons()


class Icons:

    @staticmethod
    def register():
        global icons, icons_map
        if icons is not None:
            return
        icons = bpy.utils.previews.new()
        icons_map = {"ADDON": [], "CUSTOM": []}
        from ..utils.public import ADDON_FOLDER

        icon_root = os.path.join(ADDON_FOLDER, 'src', 'icon')
        load_from_folder(icon_root, "ADDON")
        load_from_folder(os.path.join(icon_root, 'blender'), "ADDON")
        load_from_folder(os.path.join(icon_root, 'custom'), "CUSTOM")

    @staticmethod
    def _ensure_registered() -> None:
        if icons is None:
            Icons.register()

    @staticmethod
    def get(key):
        """Return preview icon; prefers loaded PNG even when name matches a built-in."""
        global icons
        Icons._ensure_registered()
        lookup = normalize_icon_name(key).lower()
        try:
            return icons[lookup]
        except KeyError as exc:
            raise KeyError(f"No preview icon for {key!r}") from exc

    @staticmethod
    def unregister() -> None:
        global icons, icons_map, _builtin_icon_names
        if icons:
            bpy.utils.previews.remove(icons)

        icons = None
        icons_map = None
        _builtin_icon_names = None
        from .texture import Texture
        Texture.clear()

    @staticmethod
    def reload_icons() -> None:
        Icons.unregister()
        Icons.register()
