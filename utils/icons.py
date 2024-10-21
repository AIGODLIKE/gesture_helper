import os

import bpy.utils.previews

icons = None
icons_map = None


def load_from_folder(icon_folder_path: str, icon_type: str) -> None:
    global icons_map
    for file in os.listdir(icon_folder_path):
        is_png = file.lower().endswith('.png')
        file_path = os.path.abspath(os.path.join(icon_folder_path, file))
        if is_png and os.path.isfile(file_path):
            name, suffix = file.split('.', 1)
            icons.load(name.lower(), file_path, 'IMAGE', force_reload=True)
            icons_map[icon_type].append(name)

            from .texture import from_image_file_path_load_texture
            from_image_file_path_load_texture(file_path)


def get_all_icons() -> list[str]:
    global icons_map
    return icons_map['ADDON'] + icons_map['BLENDER'] + icons_map['CUSTOM']


def get_blender_icons() -> list[str]:
    global icons_map
    return icons_map['BLENDER']


def check_icon(icon_identifier: str) -> bool:
    return icon_identifier in get_all_icons()


class Icons:

    @staticmethod
    def register():
        global icons, icons_map
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
    def get(key):
        global icons
        return icons[key.lower()]

    @staticmethod
    def get_all_blender_icon() -> list[str]:
        return icons_map['BLENDER']

    @staticmethod
    def unregister() -> None:
        global icons, icons_map
        bpy.utils.previews.remove(icons)

        icons = None
        icons_map = None

    @staticmethod
    def reload_icons() -> None:
        Icons.unregister()
        Icons.register()
