"""One-frame GPU command batching for recursive custom layout panels.

The layout renderer already caches semantic measurement and culls invisible
subtrees.  Its remaining hot-path cost is submitting every visible button
surface and outline as a separate GPU batch.  ``GpuLayoutBatch`` records those
primitive calls in their final model-view transforms, submits all fills in one
colored triangle batch, groups identical strokes, then replays BLF text and
icons with their original matrices.

Recording is frame-local; an immutable command snapshot may be retained while
the layout's complete visual signature stays valid.  It owns no Blender RNA
proxies, and its prepared GPU batch remains scoped to the modal session so
normal preview cleanup/reload releases it with the session cache.
"""

from __future__ import annotations

from collections import defaultdict

import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .color import color_to_gpu


def _transform_xy(matrix, point) -> tuple[float, float]:
    transformed = matrix @ Vector((float(point[0]), float(point[1]), 0.0))
    return float(transformed[0]), float(transformed[1])


class GpuLayoutBatch:
    """Collect one arranged layout frame and minimize GPU submissions."""

    __slots__ = ("_fills", "_strokes", "_content", "_prepared_fills")

    def __init__(self) -> None:
        self._fills = []
        self._strokes = []
        self._content = []
        self._prepared_fills = None

    def add_fill(
            self,
            position,
            color,
            radius,
            width,
            height,
            segments,
            corner_mask,
            matrix,
    ) -> None:
        self._fills.append((
            tuple(position),
            tuple(color),
            float(radius),
            float(width),
            float(height),
            int(segments),
            tuple(bool(value) for value in corner_mask),
            matrix.copy(),
        ))

    def add_stroke(
            self,
            points,
            color,
            line_width,
            is_cycle,
            matrix,
    ) -> None:
        self._strokes.append((
            tuple(tuple(point) for point in points),
            tuple(color),
            float(line_width),
            bool(is_cycle),
            matrix.copy(),
        ))

    def add_image(self, position, height, width, texture, matrix) -> None:
        self._content.append((
            "IMAGE",
            (tuple(position), float(height), float(width), texture),
            matrix.copy(),
        ))

    def add_text(
            self,
            text,
            position,
            size,
            color,
            font_id,
            column,
            z,
            matrix,
    ) -> None:
        self._content.append((
            "TEXT",
            (
                str(text),
                tuple(position),
                float(size),
                tuple(color),
                int(font_id),
                int(column),
                float(z),
            ),
            matrix.copy(),
        ))

    def flush(self) -> None:
        """Draw and clear all currently queued commands."""
        fills, self._fills = self._fills, []
        strokes, self._strokes = self._strokes, []
        content, self._content = self._content, []
        self._draw_commands(fills, strokes, content)

    def replay(self) -> None:
        """Redraw a retained command snapshot without rebuilding layout."""
        if self._prepared_fills is None:
            self._draw_fills(self._fills)
        else:
            self._draw_prepared_fills(self._prepared_fills)
        self._draw_strokes(self._strokes)
        self._draw_content(self._content)

    def snapshot(self):
        """Return an independent retained copy of the recorded commands."""
        retained = self.__class__()
        retained._fills = list(self._fills)
        retained._strokes = list(self._strokes)
        retained._content = list(self._content)
        retained._prepared_fills = retained._prepare_fills(retained._fills)
        return retained

    def _draw_commands(self, fills, strokes, content) -> None:
        if not fills and not strokes and not content:
            return

        self._draw_fills(fills)
        self._draw_strokes(strokes)
        self._draw_content(content)

    @staticmethod
    def _prepare_fills(commands):
        if not commands:
            return ()

        positions = []
        colors = []
        indices = []
        from .public_gpu import get_rounded_fill_mesh

        for (
                position,
                color,
                radius,
                width,
                height,
                segments,
                corner_mask,
                matrix,
        ) in commands:
            alpha = color[3] if len(color) >= 4 else 1.0
            if width <= 0.0 or height <= 0.0 or alpha <= 0.0:
                continue
            local_positions, local_indices = get_rounded_fill_mesh(
                radius,
                width,
                height,
                segments,
                corner_mask,
            )
            base = len(positions)
            px, py = position[:2]
            positions.extend(
                _transform_xy(matrix, (px + x, py + y))
                for x, y in local_positions
            )
            gpu_color = color_to_gpu(color)
            colors.extend((gpu_color,) * len(local_positions))
            indices.extend(
                (base + a, base + b, base + c)
                for a, b, c in local_indices
            )

        if not indices:
            return ()
        try:
            shader = gpu.shader.from_builtin("SMOOTH_COLOR")
            batch = batch_for_shader(
                shader,
                "TRIS",
                {"pos": positions, "color": colors},
                indices=indices,
            )
            return shader, batch
        except Exception:
            return None

    @staticmethod
    def _draw_prepared_fills(prepared) -> None:
        if not prepared:
            return
        shader, batch = prepared
        gpu.state.blend_set("ALPHA")
        with gpu.matrix.push_pop():
            gpu.matrix.load_identity()
            shader.bind()
            batch.draw(shader)

    @staticmethod
    def _draw_fills(commands) -> None:
        if not commands:
            return
        prepared = GpuLayoutBatch._prepare_fills(commands)
        if prepared is not None:
            GpuLayoutBatch._draw_prepared_fills(prepared)
            return

        # Compatibility fallback: retain the old proven primitive path if a
        # backend rejects a large colored batch.
        from .public_gpu import _draw_rounded_fill

        for command in commands:
            position, color, radius, width, height, segments, corner_mask, matrix = command
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(matrix)
                _draw_rounded_fill(
                    position,
                    color,
                    radius,
                    width,
                    height,
                    segments,
                    corner_mask,
                )

    @staticmethod
    def _draw_strokes(commands) -> None:
        if not commands:
            return

        from .gpu_stroke import build_polyline_mesh, get_stroke_shader

        shader = get_stroke_shader()
        if shader is None:
            if not GpuLayoutBatch._draw_blender_stroke_groups(commands):
                GpuLayoutBatch._draw_stroke_fallback(commands)
            return

        groups = defaultdict(lambda: ([], [], []))
        for points, color, line_width, is_cycle, matrix in commands:
            width = max(1.0, line_width)
            mesh = build_polyline_mesh(points, width, is_cycle=is_cycle)
            if mesh is None:
                continue
            local_positions, line_coords, local_indices = mesh
            key = (color_to_gpu(color), width)
            positions, coords, indices = groups[key]
            base = len(positions)
            positions.extend(
                _transform_xy(matrix, point)
                for point in local_positions
            )
            coords.extend(line_coords)
            indices.extend(
                (base + a, base + b, base + c)
                for a, b, c in local_indices
            )

        try:
            gpu.state.blend_set("ALPHA")
            with gpu.matrix.push_pop():
                gpu.matrix.load_identity()
                mvp = (
                    gpu.matrix.get_projection_matrix()
                    @ gpu.matrix.get_model_view_matrix()
                )
                for (color, line_width), (positions, coords, indices) in groups.items():
                    if not indices:
                        continue
                    batch = batch_for_shader(
                        shader,
                        "TRIS",
                        {"pos": positions, "lineCoord": coords},
                        indices=indices,
                    )
                    shader.bind()
                    shader.uniform_float("ModelViewProjectionMatrix", mvp)
                    shader.uniform_float("color", color)
                    shader.uniform_float("lineWidth", line_width)
                    batch.draw(shader)
        except Exception:
            GpuLayoutBatch._draw_stroke_fallback(commands)

    @staticmethod
    def _draw_blender_stroke_groups(commands) -> bool:
        """Batch the built-in polyline fallback by identical color/width."""
        groups = defaultdict(list)
        for points, color, line_width, is_cycle, matrix in commands:
            transformed = [_transform_xy(matrix, point) for point in points]
            if is_cycle and len(transformed) >= 2 and transformed[0] != transformed[-1]:
                transformed.append(transformed[0])
            if len(transformed) < 2:
                continue
            key = (color_to_gpu(color), max(1.0, line_width))
            positions = groups[key]
            for first, second in zip(transformed, transformed[1:]):
                positions.append((first[0], first[1], 0.0))
                positions.append((second[0], second[1], 0.0))
        if not groups:
            return True

        try:
            shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
            viewport = tuple(float(value) for value in gpu.state.viewport_get()[2:])
            gpu.state.blend_set("ALPHA")
            with gpu.matrix.push_pop():
                gpu.matrix.load_identity()
                for (color, line_width), positions in groups.items():
                    batch = batch_for_shader(
                        shader,
                        "LINES",
                        {"pos": positions},
                    )
                    shader.bind()
                    shader.uniform_float("viewportSize", viewport)
                    shader.uniform_float("lineWidth", line_width)
                    shader.uniform_float("color", color)
                    batch.draw(shader)
            return True
        except Exception:
            return False

    @staticmethod
    def _draw_stroke_fallback(commands) -> None:
        from .public_gpu import draw_line

        for points, color, line_width, is_cycle, matrix in commands:
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(matrix)
                draw_line(
                    points,
                    color,
                    line_width,
                    is_cycle=is_cycle,
                )

    @staticmethod
    def _draw_content(commands) -> None:
        if not commands:
            return
        from .public_gpu import PublicGpu

        for kind, args, matrix in commands:
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(matrix)
                if kind == "IMAGE":
                    PublicGpu.draw_image(*args)
                else:
                    text, position, size, color, font_id, column, z = args
                    PublicGpu.draw_text(
                        text,
                        position=position,
                        size=size,
                        color=color,
                        font_id=font_id,
                        column=column,
                        z=z,
                    )
