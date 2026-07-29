import gpu
from mathutils import Vector


def transform_2d_rect(matrix, rect) -> list[float]:
    """Transform a local rectangle and return its screen-space axis-aligned bounds."""
    x1, y1, x2, y2 = rect
    corners = (
        matrix @ Vector((x1, y1, 0.0)),
        matrix @ Vector((x1, y2, 0.0)),
        matrix @ Vector((x2, y1, 0.0)),
        matrix @ Vector((x2, y2, 0.0)),
    )
    xs = [float(point[0]) for point in corners]
    ys = [float(point[1]) for point in corners]
    return [min(xs), min(ys), max(xs), max(ys)]


def get_current_2d_rect(rect) -> list[float]:
    """Transform a local rectangle through the active GPU model-view matrix."""
    return transform_2d_rect(gpu.matrix.get_model_view_matrix(), rect)


def get_now_2d_offset_position() -> Vector:
    """Get current 2D offset coordinates."""
    x, y, z = gpu.matrix.get_model_view_matrix().translation
    return Vector((x, y))
