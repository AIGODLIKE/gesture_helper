import os

import bpy
import gpu
from ..utils.debug_util import debug_print


def from_image_file_path_load_texture(file_path):
    """Use icon pixels directly (32px only)
    icons = bl_ext.user_default.gesture_helper.utils.icons.icons
    i = icons.get('uv')
    buffer = gpu.types.Buffer('FLOAT',len(i.icon_pixels_float),i.icon_pixels_float)
    gpu.types.GPUTexture(i.icon_size, format='RGB16F', data = buffer)
    32,32
    """
    name = os.path.basename(file_path)[:-4]
    try:
        image = bpy.data.images.load(file_path)
        Texture.texture_list[name] = gpu.texture.from_image(image)
        bpy.data.images.remove(image)

    except Exception as e:
        debug_print(e.args, key='operator')
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
