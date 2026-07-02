import os

import bpy.utils.previews

icons = None
icons_map = None
fix_icons = {}


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

            from .texture import from_image_file_path_load_texture
            from_image_file_path_load_texture(file_path)


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


def fix_icon_pixels(key, icon):
    from .debug_util import debug_print
    global fix_icons
    if key not in fix_icons:
        fix_icons[key] = 0

    if fix_icons[key] == 10:
        icon.reload()
        debug_print("fix_icon_pixels", key, icon, key='operator')
        fix_icons[key] += 1
    else:
        fix_icons[key] += 1

        # fix_icons.append(key)
        # import numpy as np
        # pixels = np.zeros(len(icon.image_pixels), dtype=np.int32)
        # icon.image_pixels.foreach_get(pixels)
        #
        # image_pixels_float = np.zeros(len(icon.image_pixels_float), dtype=np.float32)
        # icon.image_pixels_float.foreach_get(image_pixels_float)
        # print("fix_icon_pixels", key, icon, not np.any(pixels), np.all(pixels), np.all(pixels == 0),
        #       not np.any(image_pixels_float), np.all(image_pixels_float), np.all(image_pixels_float == 0))
        # if not np.any(pixels):
        #     icon.reload()
        # else:
        #     fix_icons.append(key)


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
    def get_all_blender_icon() -> list[str]:
        Icons._ensure_registered()
        return icons_map['BLENDER']

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
