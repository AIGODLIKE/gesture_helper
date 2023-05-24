import bgl
import blf
import bpy
import gpu
from gpu.shader import from_builtin as get_shader
from gpu_extras.batch import batch_for_shader


class PublicGpu:
    _image_data = []

    @staticmethod
    def draw_2d_line(pos, color, line_width):
        shader = get_shader('2D_UNIFORM_COLOR')
        size = line_width if line_width else 1
        gpu.state.line_width_set(size)
        gpu.state.point_size_set(size)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pos})
        shader.bind()
        shader.uniform_float("color", color if color else (1.0, 1.0, 1.0, 1))
        batch.draw(shader)
        gpu.state.line_width_set(1.0)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        bgl.glPointSize(point_size)
        shader = get_shader('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        bgl.glPointSize(1)

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

        shader = get_shader('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader,
                                 'TRIS', {"pos": vertices},
                                 indices=indices)
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    @staticmethod
    def draw_2d_text(text="Hello Word",
                     size=10,
                     x: int = 100,
                     y: int = 100,
                     color=(0.5, 0.5, 0.5, 1),
                     font_id: int = 0,
                     dpi=72,
                     column=0,
                     ):
        blf.position(font_id, x, y - (size * (column + 1)), 0)
        blf.size(font_id, size, dpi)
        blf.color(font_id, *color)
        blf.draw(font_id, text)

    @staticmethod
    def draw_2d_image(image_path, x, y, width, height):
        key = f'-{image_path}'
        x2 = x + width
        y2 = y + height
        gpu.state.blend_set('ALPHA')

        if key not in PublicGpu._image_data:
            image = bpy.data.images.load(image_path)
            texture = gpu.texture.from_image(image)
            bpy.data.images.remove(image)
        else:
            texture = PublicGpu._image_data
        from gpu_extras.batch import batch_for_shader

        shader = gpu.shader.from_builtin('2D_IMAGE')
        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": ((x, y), (x2, y), (x2, y2), (x, y2)),
                "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
            },
        )
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)
