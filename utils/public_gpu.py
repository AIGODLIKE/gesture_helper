import blf
import gpu
from gpu_extras.batch import batch_for_shader


class PublicGpu:

    @staticmethod
    def draw_text(
            x: int = 0,
            y: int = 0,
            text="Hello Word",
            size=25,
            color=(1, 1, 1, 1),
            font_id: int = 0,
            column=0,
    ):
        blf.position(font_id, x, y - (size * (column + 1)), 1)
        blf.size(font_id, size)
        blf.color(font_id, *color)
        blf.draw(font_id, str(text))

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
