import os

import bpy.utils.previews

icons = None
icons_map = None


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
    return icons_map['ADDON'] + icons_map['BLENDER'] + icons_map['CUSTOM']


def get_blender_icons() -> list[str]:
    global icons_map
    Icons._ensure_registered()
    return icons_map['BLENDER']


def check_icon(icon_identifier: str) -> bool:
    return icon_identifier in get_all_icons()


def _preview_is_empty(preview) -> bool:
    icon_size = preview.icon_size
    if isinstance(icon_size, int):
        if icon_size <= 0:
            return True
    elif not icon_size or icon_size[0] <= 0 or icon_size[1] <= 0:
        return True
    return not preview.icon_pixels and not preview.icon_pixels_float


def has_empty_icons() -> bool:
    """Return True when previews are missing or contain no pixel data."""
    global icons, icons_map
    if icons is None or not icons_map:
        return True
    for names in icons_map.values():
        for name in names:
            try:
                preview = icons[name.lower()]
            except KeyError:
                return True
            if _preview_is_empty(preview):
                return True
    return False


def ensure_icons_loaded() -> bool:
    """Reload icon previews when startup left any entries empty."""
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
        icons_map = {"ADDON": [], "BLENDER": [], "CUSTOM": []}
        from ..utils.public import ADDON_FOLDER

        icon_folder = os.path.join(ADDON_FOLDER, 'src', 'icon')
        load_from_folder(icon_folder, "ADDON")

        icon_folder = os.path.join(ADDON_FOLDER, 'src', 'icon', 'blender')
        load_from_folder(icon_folder, "BLENDER")

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
        return icons[key.lower()]

    @staticmethod
    def unregister() -> None:
        global icons, icons_map
        if icons:
            bpy.utils.previews.remove(icons)

        icons = None
        icons_map = None
        from .texture import Texture
        Texture.clear()

    @staticmethod
    def reload_icons() -> None:
        Icons.unregister()
        Icons.register()
