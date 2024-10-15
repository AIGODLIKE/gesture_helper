import os

import bpy
import gpu


def from_image_file_path_load_texture(file_path):
    name, suffix = os.path.basename(file_path).split('.')
    try:
        image = bpy.data.images.load(file_path)
        Texture.texture_list[name] = gpu.texture.from_image(image)
        bpy.data.images.remove(image)

    except Exception as e:
        print(e.args)
        import traceback
        traceback.print_exc()
        traceback.print_stack()


class Texture:
    texture_list = {}

    @staticmethod
    def clear():
        Texture.texture_list.clear()

    @staticmethod
    def get_texture(key):
        return Texture.texture_list.get(key)
