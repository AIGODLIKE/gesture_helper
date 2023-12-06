import os

import bpy.utils.previews


class Icons:
    __icons__ = bpy.utils.previews.new()

    @classmethod
    def init(cls):
        from .public import ADDON_FOLDER
        icon_folder = os.path.join(ADDON_FOLDER, r'src\icon')
        for file in os.listdir(icon_folder):
            name, suffix = file.split('.')
            file_path = os.path.abspath(os.path.join(icon_folder, file))
            is_png = file.lower().endswith('.png')
            if is_png and os.path.isfile(file_path):
                cls.__icons__.load(name.lower(), file_path, 'IMAGE', force_reload=True)

    @classmethod
    def get(cls, key):
        return cls.__icons__[key.lower()]
