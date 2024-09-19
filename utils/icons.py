import os

import bpy.utils.previews

icons = None


class Icons:

    @classmethod
    def register(cls):
        global icons
        icons = bpy.utils.previews.new()
        from ..utils.public import ADDON_FOLDER
        icon_folder = os.path.join(ADDON_FOLDER, 'src', 'icon')
        for file in os.listdir(icon_folder):
            name, suffix = file.split('.')
            file_path = os.path.abspath(os.path.join(icon_folder, file))
            is_png = file.lower().endswith('.png')
            if is_png and os.path.isfile(file_path):
                icons.load(name.lower(), file_path, 'IMAGE', force_reload=True)

    @classmethod
    def get(cls, key):
        global icons
        return icons[key.lower()]

    @classmethod
    def unregister(cls):
        global icons
        bpy.utils.previews.remove(icons)
