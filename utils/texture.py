import os

import bpy
import gpu


class Texture:
    texture_list = {}

    @classmethod
    def register(cls):
        from ..utils.public import ADDON_FOLDER
        icon_folder = os.path.join(ADDON_FOLDER, r'src\icon')
        for file in os.listdir(icon_folder):
            name, suffix = file.split('.')
            file_path = os.path.abspath(os.path.join(icon_folder, file))
            is_png = file.lower().endswith('.png')
            if is_png and os.path.isfile(file_path):
                try:
                    image = bpy.data.images.load(file_path)
                    cls.texture_list[name] = gpu.texture.from_image(image)
                    bpy.data.images.remove(image)
                except Exception as e:
                    print(e.args)
                    import traceback
                    traceback.print_exc()
                    traceback.print_stack()

    @classmethod
    def unregister(cls):
        cls.texture_list.clear()

    @classmethod
    def get(cls, key):
        return cls.texture_list.get(key)
