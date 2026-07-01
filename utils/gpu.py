import gpu
from mathutils import Vector


def get_now_2d_offset_position() -> Vector:
    """Get current 2D offset coordinates."""
    x, y, z = gpu.matrix.get_model_view_matrix().translation
    return Vector((x, y))
