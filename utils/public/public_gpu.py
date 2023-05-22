import bgl
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

if bpy.app.background:  # 后台运行
    _2D_SMOOTH_COLOR = _2D_UNIFORM_COLOR_SHADER = _2D_IMAGE_SHADER = None

else:
    _2D_IMAGE_SHADER = gpu.shader.from_builtin('2D_IMAGE')
    _2D_UNIFORM_COLOR_SHADER = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    _2D_SMOOTH_COLOR = gpu.shader.from_builtin('2D_SMOOTH_COLOR')


class PublicGpu:
    @staticmethod
    def draw_2d_line(pos, color, line_width):
        shader = _2D_UNIFORM_COLOR_SHADER
        gpu.state.line_width_set(line_width if line_width else 1)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pos})
        shader.bind()

        shader.uniform_float("color", color if color else (1.0, 1.0, 1.0, 1))
        batch.draw(shader)
        gpu.state.line_width_set(1.0)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 0.5)):
        bgl.glPointSize(point_size)
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        bgl.glPointSize(1)

    @staticmethod
    def draw_2d_rectangle(x: int, y: int, x2: int, y2: int, color=(0, 0, 0, 0.5)):
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
            x (int): _description_
            y (int): _description_
            x2 (int): _description_
            y2 (int): _description_
            """
        vertices = ((x, y), (x2, y), (x, y2), (x2, y2))
        indices = ((0, 1, 2), (2, 1, 3))

        shader = _2D_UNIFORM_COLOR_SHADER
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
        blf.draw(font_id, text)
        blf.color(font_id, *color)
