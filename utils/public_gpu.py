import math

import blf
import gpu
from gpu_extras.batch import batch_for_shader


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
        x = position[0]
        y = position[1]
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
        from math import sin, cos, pi
        import gpu
        from gpu.types import (
            GPUBatch,
            GPUVertBuf,
            GPUVertFormat,
        )

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            gpu.matrix.scale_uniform(radius)
            gpu.state.line_width_set(line_width)
            mul = (1.0 / (segments - 1)) * (pi * 2)
            verts = [(sin(i * mul), cos(i * mul)) for i in range(segments)]
            fmt = GPUVertFormat()
            pos_id = fmt.attr_add(id="pos",
                                  comp_type='F32',
                                  len=2,
                                  fetch_mode='FLOAT')
            vbo = GPUVertBuf(len=len(verts), format=fmt)
            vbo.attr_fill(id=pos_id, data=verts)
            batch = GPUBatch(type='LINE_STRIP', buf=vbo)
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch.program_set(shader)
            shader.uniform_float("color", color)
            batch.draw()

    @staticmethod
    def draw_rounded_rectangle_frame(position, *, color=(0, 0, 0, 1), radius=10, width=200, height=200, segments=32):
        import gpu
        from gpu.types import (
            GPUBatch,
            GPUVertBuf,
            GPUVertFormat,
        )

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            verts = PublicGpu.get_rounded_rectangle_vertex(radius, width, height, segments)

            fmt = GPUVertFormat()
            pos_id = fmt.attr_add(id="pos",
                                  comp_type='F32',
                                  len=2,
                                  fetch_mode='FLOAT')
            vbo = GPUVertBuf(len=len(verts), format=fmt)
            vbo.attr_fill(id=pos_id, data=verts)
            batch = GPUBatch(type='LINE_STRIP', buf=vbo)
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch.program_set(shader)
            shader.uniform_float("color", color)
            batch.draw()

    @staticmethod
    def draw_rounded_rectangle_area(position, color=(1, 1, 1, 1.0), *, radius=10, width=200, height=200,
                                    segments=10):
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = PublicGpu.get_rounded_rectangle_vertex(radius, width, height, segments)
            indices = PublicGpu.get_indices_from_vertex(vertex)
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(shader, 'TRIS', {"pos": vertex}, indices=indices)
            shader.uniform_float("color", color)
            batch.draw(shader)

    @staticmethod
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
            # if not segments % i:
            #     qa(quadrant[(s + 1) % 4], angle)
            qa(q, angle)
        vertex.append(vertex[0])
        return vertex

    @staticmethod
    def get_indices_from_vertex(vertex):
        indices = []
        for i in range(len(vertex) - 2):
            indices.append((0, i + 1, i + 2))
        return indices

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        gpu.state.point_size_set(point_size)
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
