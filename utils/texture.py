import os

import bpy
import gpu


def from_image_file_path_load_texture(file_path):
    """可以直接使用图标的像素，但是只有32像素
    icons = bl_ext.user_default.gesture_helper.utils.icons.icons
    i = icons.get('uv')
    buffer = gpu.types.Buffer('FLOAT',len(i.icon_pixels_float),i.icon_pixels_float)
    gpu.types.GPUTexture(i.icon_size, format='RGB16F', data = buffer)
    32,32
    """
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
