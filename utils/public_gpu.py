import math
import re
from functools import cache

import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Euler, Vector


@cache
def from_segments_generator_circle_verts(segments):
    from math import sin, cos, pi
    mul = (1.0 / (segments - 1)) * (pi * 2)
    verts = [(sin(i * mul), cos(i * mul), 0) for i in range(segments)]
    return tuple(verts)


def draw_line(verts, color, line_width, is_cycle=True):
    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    shader.uniform_float("lineWidth", line_width)
    shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
    pos = []
    colors = []
    vl = len(verts)
    for index, v in enumerate(verts):
        pos.append(v)
        colors.append(color)
        if vl - 1 == index:
            if is_cycle:
                pos.append(verts[0])
                colors.append(color)
        else:
            colors.append(color)
            pos.append(verts[index + 1])
    shader.bind()

    batch = batch_for_shader(shader, 'LINES', {"pos": pos, "color": colors})
    batch.draw(shader)


@cache
def get_rounded_rectangle_vertex(radius=10, width=200, height=200, segments=10):
    if segments <= 0:
        raise ValueError("Amount of segments must be greater than 0.")
    rounded_segments = segments * 4  # 圆角的边
    w = int((width - radius) / 2) - radius / 2
    h = int((height - radius) / 2) - radius / 2
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

    def qa(qq, a):
        x = qq[0] + radius * math.cos(a)
        y = qq[1] + radius * math.sin(a)
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
        b = math.radians(angle_step * (1 + i))
        x = math.cos(b)
        y = math.sin(b)
        vertex.append((x, y))
    return tuple(vertex)


@cache
def get_indices_from_vertex(vertex):
    indices = []
    for i in range(len(vertex) - 2):
        indices.append((0, i + 1, i + 2))
    return indices


def contains_chinese(text):
    if not isinstance(text, str):
        return False
    pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(pattern.search(text))


class PublicGpu:
    @staticmethod
    def draw_image(position, height, width, texture):
        shader = gpu.shader.from_builtin('IMAGE')
        gpu.matrix.translate(position)
        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": ((0, 0), (width, 0), (width, height), (0, height)),
                "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
            },
        )
        shader.bind()
        shader.uniform_sampler("image", texture)

        with gpu.matrix.push_pop():
            batch.draw(shader)

    @staticmethod
    def draw_text(
            position,
            text="Hello Word",
            size=25,
            color=(1, 1, 1, 1),
            font_id=0,
            column=0,
    ):
        with gpu.matrix.push_pop():
            if contains_chinese(text):
                (width, height) = blf.dimensions(font_id, text)
                gpu.matrix.translate(Vector([0, -height * .075]))

            x, y = position
            blf.size(font_id, size)
            blf.color(font_id, *color)
            blf.position(font_id, x, y - (size * (column + 1)), 1)
            blf.draw(font_id, str(text))

    @staticmethod
    def draw_2d_line(pos, color=(1.0, 1.0, 1.0, 1), line_width=1):
        draw_line(pos, color, line_width, is_cycle=False)

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
            draw_line(verts, color, line_width)

    @staticmethod
    def draw_arc(position, radius, angle, arc, color=(0.4, 0.3, 0.8, 1), line_width=2, segments=128):
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            gpu.matrix.scale_uniform(radius)
            gpu.state.line_width_set(line_width)
            a = Euler((0, 0, -arc * 2 / 360), 'XYZ').to_matrix()
            e = Euler((0, 0, angle * 3 / 180), 'XYZ').to_matrix()
            gpu.matrix.multiply_matrix(e.to_4x4() @ a.to_4x4())

            verts = get_arc_vertex(arc, segments)
            draw_line(verts, color, line_width, is_cycle=False)

    @staticmethod
    def draw_rounded_rectangle_frame(position, *, color=(0, 0, 0, 1), line_width=2, radius=10, width=200, height=200,
                                     segments=128):
        import gpu

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(radius, width, height, segments)
            draw_line(vertex, color, line_width=line_width)

    @staticmethod
    def draw_rounded_rectangle_area(position, color=(1, 1, 1, 1.0), *, radius=10, width=200, height=200,
                                    segments=20):
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(radius, width, height, segments)
            indices = get_indices_from_vertex(vertex)
            shader = gpu.shader.from_builtin('SMOOTH_COLOR')
            batch = batch_for_shader(shader,
                                     'TRIS',
                                     {"pos": vertex, "color": [color for _ in range(len(vertex))]},
                                     indices=indices)
            batch.draw(shader)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        gpu.state.point_size_set(point_size)
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
