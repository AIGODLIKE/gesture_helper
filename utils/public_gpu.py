import math
from functools import cache

import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Euler


@cache
def from_segments_generator_circle_verts(segments):
    from math import sin, cos, pi
    mul = (1.0 / (segments - 1)) * (pi * 2)
    verts = [(sin(i * mul), cos(i * mul)) for i in range(segments)]
    return tuple(verts)


@cache
def get_batch(verts):
    from gpu.types import (
        GPUBatch,
        GPUVertBuf,
        GPUVertFormat,
    )
    fmt = GPUVertFormat()
    pos_id = fmt.attr_add(id="pos",
                          comp_type='F32',
                          len=2,
                          fetch_mode='FLOAT')
    vbo = GPUVertBuf(len=len(verts), format=fmt)
    vbo.attr_fill(id=pos_id, data=verts)
    batch = GPUBatch(type='LINE_STRIP', buf=vbo)
    return batch


@cache
def get_shader(name='UNIFORM_COLOR'):
    return gpu.shader.from_builtin(name)


def from_vert_get_draw_batch(verts, color):
    batch = get_batch(verts)
    shader = get_shader()
    batch.program_set(shader)
    shader.uniform_float("color", color)
    return batch


@cache
def get_rounded_rectangle_vertex(radius=10, width=200, height=200, segments=10):
    if segments <= 0:
        raise ValueError("Amount of segments must be greater than 0.")
    rounded_segments = segments * 4  # 圆角的边
    w = (width - radius) / 2
    h = (height - radius) / 2
    # 角度步长，通常以度为单位
    # 存储顶点坐标的列表
    vertex = []
    quadrant = {
        1: (w, h),
        2: (-w, h),
        3: (-w, -h),
        4: (w, -h),
    }
    angle_step = 360 / rounded_segments  # 这里选择了8个顶点，可以根据需要调整

    def qa(q, a):
        x = q[0] + radius * math.cos(a)
        y = q[1] + radius * math.sin(a)
        vertex.append((x, y))

    # 计算顶点坐标
    for i in range(rounded_segments):
        angle = math.radians(i * angle_step)  # 将角度转换为弧度
        s = i // segments
        q = quadrant[s + 1]
        qa(q, angle)
    vertex.append(vertex[0])
    return tuple(vertex)


@cache
def get_arc_vertex(arc, segments=40):
    vertex = []
    angle_step = arc / segments
    for i in range(segments):
        b = math.radians(1 + angle_step * i)
        x = math.cos(1 + b)
        y = math.sin(1 + b)
        vertex.append((x, y))
    return tuple(vertex)


@cache
def get_indices_from_vertex(vertex):
    indices = []
    for i in range(len(vertex) - 2):
        indices.append((0, i + 1, i + 2))
    return indices


class PublicGpu:

    @staticmethod
    def draw_text(
            position,
            text="Hello Word",
            size=25,
            color=(1, 1, 1, 1),
            font_id: int = 0,
            column=0,
    ):
        x, y = position
        blf.position(font_id, x, y - (size * (column + 1)), 1)
        blf.size(font_id, size)
        blf.color(font_id, *color)
        blf.draw(font_id, str(text))

    @staticmethod
    def draw_2d_line(pos, color=(1.0, 1.0, 1.0, 1), line_width=1):
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(line_width)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pos})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.line_width_set(1.0)

    @staticmethod
    def draw_rectangle(x, y, width, height, color=(0, 0, 0, 1.0)):
        x2, y2 = x + width, y + height
        PublicGpu.draw_2d_rectangle(x, y, x2, y2, color)

    @staticmethod
    def draw_2d_rectangle(x: int, y: int, x2: int, y2: int, color=(0, 0, 0, 1.0)):
        """左下角为初始坐标
        ┌────────────────────────────┐
        │                       x2y2 │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │ xy                         │
        └────────────────────────────┘


        Args:
            :param y2:
            :param x2:
            :param y:
            :param x:
            :param color:
            """
        vertices = ((x, y), (x2, y), (x, y2), (x2, y2))
        indices = ((0, 1, 2), (2, 1, 3))

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader,
                                 'TRIS', {"pos": vertices},
                                 indices=indices)
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    @staticmethod
    def draw_circle(position, radius, *, color=(1, 1, 1, 1.0), line_width=2, segments=128):

        from math import pi, ceil, acos
        import gpu

        if segments is None:
            max_pixel_error = 0.25  # TODO: multiply 0.5 by display dpi
            segments = int(ceil(pi / acos(1.0 - max_pixel_error / radius)))
            segments = max(segments, 8)
            segments = min(segments, 1000)

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            gpu.matrix.scale_uniform(radius)
            gpu.state.line_width_set(line_width)
            verts = from_segments_generator_circle_verts(segments)

            batch = from_vert_get_draw_batch(verts, color)
            batch.draw()

    @staticmethod
    def draw_arc(position, radius, angle, arc, color=(0, 0, 0, 1), line_width=2, segments=30):

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            gpu.matrix.scale_uniform(radius)
            gpu.state.line_width_set(line_width)

            normal_matrix = gpu.matrix.get_normal_matrix()
            e = Euler((0, 0, angle - arc / 2)).to_matrix()
            gpu.matrix.multiply_matrix((normal_matrix @ e).to_4x4())

            verts = get_arc_vertex(arc, segments)
            batch = from_vert_get_draw_batch(verts, color)
            batch.draw()

    @staticmethod
    def draw_rounded_rectangle_frame(position, *, color=(0, 0, 0, 1), radius=10, width=200, height=200, segments=32):
        import gpu

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(radius, width, height, segments)

            batch = from_vert_get_draw_batch(vertex, color)
            batch.draw()
            batch.draw()

    @staticmethod
    def draw_rounded_rectangle_area(position, color=(1, 1, 1, 1.0), *, radius=10, width=200, height=200,
                                    segments=10):
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(radius, width, height, segments)
            indices = get_indices_from_vertex(vertex)
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(shader, 'TRIS', {"pos": vertex}, indices=indices)
            shader.uniform_float("color", color)
            batch.draw(shader)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        gpu.state.point_size_set(point_size)
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
