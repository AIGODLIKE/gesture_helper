import os

import bpy
import gpu
from ..utils.debug_util import debug_print


def from_image_file_path_load_texture(file_path):
    """Load PNG icon into GPU texture cache (32px icons)."""
    name = os.path.basename(file_path)[:-4].lower()
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
    def _texture_from_icon_preview(key: str):
        from .icons import Icons

        try:
            preview = Icons.get(key)
        except KeyError:
            return None

        icon_size = preview.icon_size
        if isinstance(icon_size, int):
            width = height = icon_size
        else:
            width, height = icon_size[0], icon_size[1]
        if width <= 0 or height <= 0:
            return None

        pixels = preview.icon_pixels_float
        if not pixels:
            return None

        buffer = gpu.types.Buffer('FLOAT', len(pixels), pixels)
        return gpu.types.GPUTexture((width, height), format='RGBA32F', data=buffer)

    @staticmethod
    def get_texture(key):
        if not key:
            return None

        lookup = key.lower()
        texture = Texture.texture_list.get(lookup)
        if texture is not None:
            return texture

        texture = Texture._texture_from_icon_preview(lookup)
        if texture is not None:
            Texture.texture_list[lookup] = texture
        return texture
