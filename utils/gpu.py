import gpu
from mathutils import Vector


def get_now_2d_offset_position() -> Vector:
    """获取当前2d偏移坐标"""
    x, y, z = gpu.matrix.get_model_view_matrix().translation
    return Vector((x, y))
