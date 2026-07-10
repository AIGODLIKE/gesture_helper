import os

import bpy
import bpy.utils.previews

icons = None
icons_map = None
_builtin_icon_names: frozenset[str] | None = None


def get_builtin_icon_names() -> frozenset[str]:
    """Return Blender built-in icon identifiers from the UI layout RNA enum."""
    global _builtin_icon_names
    if _builtin_icon_names is None:
        _builtin_icon_names = frozenset(
            bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()
        )
    return _builtin_icon_names


def is_builtin_icon(icon_name: str) -> bool:
    return bool(icon_name) and icon_name in get_builtin_icon_names()


def icon_layout_kwargs(icon_name: str) -> dict:
    """Return ``icon`` or ``icon_value`` kwargs for UILayout widgets."""
    if is_builtin_icon(icon_name):
        return {"icon": icon_name}
    Icons._ensure_registered()
    try:
        return {"icon_value": icons[icon_name.lower()].icon_id}
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
            name, suffix = file.split('.', 1)
            icons.load(name.lower(), file_path, 'IMAGE', force_reload=True)
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
    if not icon_identifier:
        return False
    if is_builtin_icon(icon_identifier):
        return True
    Icons._ensure_registered()
    return icon_identifier.lower() in icons


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

        icon_folder = os.path.join(ADDON_FOLDER, 'src', 'icon')
        load_from_folder(icon_folder, "ADDON")

        icon_folder = os.path.join(ADDON_FOLDER, 'src', 'icon', 'custom')
        load_from_folder(icon_folder, "CUSTOM")

    @staticmethod
    def _ensure_registered() -> None:
        if icons is None:
            Icons.register()

    @staticmethod
    def get(key):
        global icons
        Icons._ensure_registered()
        if is_builtin_icon(key):
            raise KeyError(f"{key!r} is a built-in Blender icon, not a preview icon")
        return icons[key.lower()]

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
