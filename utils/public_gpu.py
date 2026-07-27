import math
from functools import cache

import blf
import gpu
from gpu_extras.batch import batch_for_shader
from .color import clear_color_cache, color_to_gpu, color_to_srgb, linear_to_srgb_tuple

# Default corner tessellation (segments per 90° quadrant).
DEFAULT_ROUND_SEGMENTS = 48
DEFAULT_CIRCLE_SEGMENTS = 64

_SHADER_CACHE: dict[str, object] = {}
# key -> (shader_identity, batch); rebuild when shader instance changes after reload.
_ROUNDED_FILL_BATCH: dict[tuple, tuple] = {}
_IMAGE_BATCH_CACHE: dict[tuple[float, float], tuple] = {}

_GPU_DRAW_DEPTH = 0
_SAVED_BLEND = None
_SAVED_DEPTH_TEST = None


def _get_shader(name: str):
    shader = _SHADER_CACHE.get(name)
    if shader is None:
        shader = gpu.shader.from_builtin(name)
        _SHADER_CACHE[name] = shader
    return shader


def _point_shader():
    try:
        return _get_shader('POINT_UNIFORM_COLOR')
    except Exception:
        return _get_shader('UNIFORM_COLOR')


def clear_gpu_caches() -> None:
    """Drop module-level GPU batches/shaders and geometry caches (reload-safe)."""
    global _GPU_DRAW_DEPTH, _SAVED_BLEND, _SAVED_DEPTH_TEST
    _SHADER_CACHE.clear()
    _ROUNDED_FILL_BATCH.clear()
    _IMAGE_BATCH_CACHE.clear()
    from_segments_generator_circle_vertex.cache_clear()
    get_rounded_rectangle_vertex.cache_clear()
    get_arc_vertex.cache_clear()
    get_rounded_fill_mesh.cache_clear()
    clear_color_cache()
    from .blf_text import clear_text_metrics
    clear_text_metrics()
    try:
        from ..element.element_gpu_draw import from_text_get_dimensions
        from_text_get_dimensions.cache_clear()
    except Exception:
        pass
    _GPU_DRAW_DEPTH = 0
    _SAVED_BLEND = None
    _SAVED_DEPTH_TEST = None
    try:
        from .gpu_stroke import clear_stroke_shader_cache
        clear_stroke_shader_cache()
    except Exception:
        pass
    try:
        from ..src.lib.overlay_layout import clear_overlay_shader
        clear_overlay_shader()
    except Exception:
        pass


def gpu_draw_begin():
    """Enter a 2D HUD draw frame: set blend/depth once, nestable."""
    global _GPU_DRAW_DEPTH, _SAVED_BLEND, _SAVED_DEPTH_TEST
    if _GPU_DRAW_DEPTH == 0:
        _SAVED_BLEND = gpu.state.blend_get()
        _SAVED_DEPTH_TEST = gpu.state.depth_test_get()
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')
    _GPU_DRAW_DEPTH += 1


def gpu_draw_end():
    """Leave a 2D HUD draw frame and restore GPU state when outermost."""
    global _GPU_DRAW_DEPTH, _SAVED_BLEND, _SAVED_DEPTH_TEST
    if _GPU_DRAW_DEPTH <= 0:
        return
    _GPU_DRAW_DEPTH -= 1
    if _GPU_DRAW_DEPTH == 0:
        if _SAVED_BLEND is not None:
            gpu.state.blend_set(_SAVED_BLEND)
        if _SAVED_DEPTH_TEST is not None:
            gpu.state.depth_test_set(_SAVED_DEPTH_TEST)
        _SAVED_BLEND = None
        _SAVED_DEPTH_TEST = None


def _ensure_alpha_blend():
    gpu.state.blend_set('ALPHA')


@cache
def from_segments_generator_circle_vertex(segments) -> tuple:
    from math import sin, cos, pi
    mul = (1.0 / (segments - 1)) * (pi * 2)
    return tuple((sin(i * mul), cos(i * mul), 0) for i in range(segments))


def _as_vec3(v):
    """POLYLINE shaders expect vec3 positions."""
    if len(v) >= 3:
        return float(v[0]), float(v[1]), float(v[2])
    return float(v[0]), float(v[1]), 0.0


def _polyline_positions(vertex, is_cycle=True):
    """Build a continuous LINE_STRIP position list (optionally closed)."""
    if not vertex:
        return []
    pos = [_as_vec3(v) for v in vertex]
    if is_cycle and len(pos) >= 2 and pos[0] != pos[-1]:
        pos.append(pos[0])
    return pos


def _as_rgba(color):
    """Scene-linear ColorProperty / RGBA → GPU overlay uniform."""
    from .color import color_to_gpu
    c = tuple(color)
    if len(c) == 3:
        c = (c[0], c[1], c[2], 1.0)
    return color_to_gpu(c)


def draw_line(vertex, color, line_width, is_cycle=True) -> None:
    """Draw a gap-less AA polyline (round joins + SDF fringe)."""
    if not vertex or len(vertex) < 2:
        return

    from .gpu_stroke import draw_blender_polyline, draw_smooth_stroke

    # 1) Custom round-join stroke (fills sharp-corner wedges).
    if draw_smooth_stroke(vertex, color, line_width, is_cycle=is_cycle):
        return
    # 2) Built-in POLYLINE fallback (butt joins; may gap at sharp turns).
    if draw_blender_polyline(vertex, color, line_width, is_cycle=is_cycle):
        return

    # 3) Last-resort thin line.
    pos = _polyline_positions(vertex, is_cycle=is_cycle)
    if len(pos) < 2:
        return
    _ensure_alpha_blend()
    shader = _get_shader('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pos})
    shader.bind()
    try:
        shader.uniform_float("color", _as_rgba(color))
    except Exception:
        pass
    batch.draw(shader)


def _round_rect_segments(radius: float, segments: int) -> int:
    """Adaptive corner tessellation — small radii need fewer steps."""
    # ~0.35px chord error: segments ≈ π*r / (2*sqrt(2*r*err))
    r = max(0.5, float(radius))
    auto = int(math.ceil(math.pi * r / (2.0 * math.sqrt(max(2.0 * r * 0.35, 1e-4)))))
    return max(4, min(int(segments), auto, 32))


def _clamp_rounded_radius(radius, width, height) -> float:
    """Clamp a radius only to the actual rectangle dimensions."""
    return min(
        max(0.0, float(radius)),
        max(0.0, float(width)) * 0.5,
        max(0.0, float(height)) * 0.5,
    )


@cache
def get_rounded_rectangle_vertex(
        radius=10,
        width=200,
        height=200,
        segments=12,
        corner_mask=(True, True, True, True),
) -> tuple:
    """Outline vertices for a centered rounded rect (CCW, Y-up).

    Each corner contributes ``segments + 1`` samples, including both tangent
    endpoints, so opposite corners and all four straight edges are symmetric.
    ``corner_mask`` is ``(top-left, top-right, bottom-right, bottom-left)``.
    """
    if segments <= 0:
        raise ValueError("Amount of segments must be greater than 0.")
    radius = _clamp_rounded_radius(radius, width, height)
    segments = _round_rect_segments(radius, segments)
    hw = width * 0.5 - radius
    hh = height * 0.5 - radius
    top_left, top_right, bottom_right, bottom_left = (
        bool(value) for value in corner_mask
    )
    round_flags = (top_right, top_left, bottom_left, bottom_right)
    square_points = (
        (width * 0.5, height * 0.5),
        (-width * 0.5, height * 0.5),
        (-width * 0.5, -height * 0.5),
        (width * 0.5, -height * 0.5),
    )
    # Corner centers: TR, TL, BL, BR — each arc covers 90°.
    corners = (
        (hw, hh, 0.0),        # TR: 0 → 90
        (-hw, hh, 90.0),      # TL: 90 → 180
        (-hw, -hh, 180.0),    # BL: 180 → 270
        (hw, -hh, 270.0),     # BR: 270 → 360
    )
    vertex = []
    step = 90.0 / segments
    for index, (cx, cy, start) in enumerate(corners):
        if not round_flags[index]:
            vertex.append(square_points[index])
            continue
        for j in range(segments + 1):
            a = math.radians(start + step * j)
            vertex.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return tuple(vertex)


@cache
def get_arc_vertex(arc, segments=40):
    """Unit-circle arc from 0° to ``arc`` degrees (inclusive endpoints)."""
    segments = max(1, int(segments))
    vertex = []
    for i in range(segments + 1):
        b = math.radians(float(arc) * i / segments)
        vertex.append((math.cos(b), math.sin(b)))
    return tuple(vertex)


@cache
def get_rounded_fill_mesh(
        radius,
        width,
        height,
        segments,
        corner_mask=(True, True, True, True),
):
    """Center-fan mesh for a filled rounded rect."""
    segs = _round_rect_segments(radius, segments)
    outline = get_rounded_rectangle_vertex(radius, width, height, segs, corner_mask)
    verts = ((0.0, 0.0),) + outline
    n = len(outline)
    indices = tuple((0, i, i + 1) for i in range(1, n)) + ((0, n, 1),)
    return verts, indices


def _get_rounded_fill_batch(radius, width, height, segments, corner_mask):
    segs = _round_rect_segments(radius, segments)
    corner_mask = tuple(bool(value) for value in corner_mask)
    key = (
        round(radius, 3), round(width, 3), round(height, 3), int(segs), corner_mask,
    )
    shader = _get_shader('UNIFORM_COLOR')
    entry = _ROUNDED_FILL_BATCH.get(key)
    if entry is not None and entry[0] is shader:
        return entry[1]
    verts, indices = get_rounded_fill_mesh(radius, width, height, segs, corner_mask)
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
    _ROUNDED_FILL_BATCH[key] = (shader, batch)
    return batch


def _draw_rounded_fill(position, color, radius, width, height, segments, corner_mask):
    if width <= 0 or height <= 0:
        return
    r = _clamp_rounded_radius(radius, width, height)
    _ensure_alpha_blend()
    shader = _get_shader('UNIFORM_COLOR')
    batch = _get_rounded_fill_batch(r, width, height, segments, corner_mask)
    with gpu.matrix.push_pop():
        gpu.matrix.translate(position)
        shader.bind()
        shader.uniform_float("color", _as_rgba(color))
        batch.draw(shader)


# Re-export for existing call sites.
__all__ = [
    'PublicGpu',
    'color_to_srgb',
    'color_to_gpu',
    'linear_to_srgb_tuple',
    'clear_gpu_caches',
    'draw_line',
    'gpu_draw_begin',
    'gpu_draw_end',
]


class PublicGpu:
    @staticmethod
    def draw_image(position, height, width, texture):
        if texture is None:
            return
        # Always force ALPHA — icon textures rely on straight alpha; never inherit
        # a dirty blend state from prior stroke/fill draws.
        gpu.state.blend_set('ALPHA')
        key = (float(width), float(height))
        shader = _get_shader('IMAGE')
        entry = _IMAGE_BATCH_CACHE.get(key)
        if entry is not None and entry[0] is shader:
            batch = entry[1]
        else:
            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {
                    "pos": ((0, 0), (width, 0), (width, height), (0, height)),
                    "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
                },
            )
            _IMAGE_BATCH_CACHE[key] = (shader, batch)
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            shader.bind()
            shader.uniform_sampler("image", texture)
            batch.draw(shader)

    @staticmethod
    def draw_text(
            text="",
            position=(0, 0),
            size=25,
            color=(1, 1, 1, 1),
            font_id=0,
            column=0,
            z=1,
    ):
        """Draw *text* with its line box top at ``position``.

        The baseline sits ``ascent`` below the top (measured metrics, not the
        font size), so any label — CJK, capitals, descenders — occupies the
        same stable line box instead of jumping with its ink extents.
        """
        from .blf_text import line_metrics
        x, y = position
        ascent, _descent, line_h = line_metrics(size, font_id)
        blf.disable(font_id, blf.CLIPPING)
        blf.disable(font_id, blf.MONOCHROME)
        blf.size(font_id, size)
        blf.color(font_id, *color)
        blf.position(font_id, x, y - ascent - line_h * column, z)
        blf.draw(font_id, str(text))

    @classmethod
    def draw_annotation_row(
            cls,
            text,
            *,
            anchor_rect,
            viewport_size,
            size,
            scale=1.0,
            fill=(0.08, 0.08, 0.08, 0.96),
            stroke=(0.35, 0.35, 0.35, 0.8),
            accent=(0.25, 0.5, 0.9, 1.0),
            text_color=(1.0, 1.0, 1.0, 1.0),
            mark="i",
            max_lines=2,
    ):
        """Draw a compact annotation beside an existing runtime item."""
        if not text or anchor_rect is None:
            return None
        from .blf_text import measure_text, wrap_text

        viewport_w, viewport_h = (float(value) for value in viewport_size)
        scale = max(0.5, float(scale))
        margin = max(6.0, 8.0 * scale)
        gap = max(4.0, 5.0 * scale)
        pad_x = max(7.0, 8.0 * scale)
        pad_y = max(4.0, 5.0 * scale)
        icon_gap = max(5.0, 6.0 * scale)
        _sample_w, line_h = measure_text("Ag", size)
        icon_size = max(14.0 * scale, line_h)
        max_width = max(
            1.0,
            min(520.0 * scale, viewport_w - margin * 2.0),
        )
        text_max_width = max(
            1.0,
            max_width - pad_x * 2.0 - icon_size - icon_gap,
        )
        lines = wrap_text(
            text,
            text_max_width,
            size,
            max_lines=max_lines,
        )
        if not lines:
            return None

        text_w = max(measure_text(line, size)[0] for line in lines)
        content_w = pad_x * 2.0 + icon_size + icon_gap + text_w
        anchor_x1, anchor_y1, anchor_x2, anchor_y2 = (
            float(value) for value in anchor_rect
        )
        anchor_w = max(0.0, anchor_x2 - anchor_x1)
        width = min(max_width, max(content_w, min(anchor_w, max_width)))
        height = max(
            icon_size + pad_y * 2.0,
            line_h * len(lines) + pad_y * 2.0,
        )

        center_x = (anchor_x1 + anchor_x2) * 0.5
        center_x = min(
            viewport_w - margin - width * 0.5,
            max(margin + width * 0.5, center_x),
        )
        below_top = anchor_y1 - gap
        if below_top - height >= margin:
            top = below_top
        elif anchor_y2 + gap + height <= viewport_h - margin:
            top = anchor_y2 + gap + height
        else:
            top = min(viewport_h - margin, max(margin + height, below_top))
        bottom = top - height
        center_y = bottom + height * 0.5

        cls.draw_rounded_rectangle_outlined(
            (center_x, center_y),
            fill=fill,
            stroke=stroke,
            radius=min(5.0 * scale, height * 0.2),
            width=width,
            height=height,
            line_width=max(0.75, scale),
        )

        left = center_x - width * 0.5 + pad_x
        cls.draw_rounded_rectangle_area(
            (left + icon_size * 0.5, center_y),
            color=accent,
            radius=min(3.0 * scale, icon_size * 0.22),
            width=icon_size,
            height=icon_size,
        )
        mark_w, _mark_h = measure_text(mark, size)
        cls.draw_text(
            mark,
            position=(left + (icon_size - mark_w) * 0.5, center_y + line_h * 0.5),
            size=size,
            color=(1.0, 1.0, 1.0, 0.98),
        )

        text_x = left + icon_size + icon_gap
        text_top = center_y + line_h * len(lines) * 0.5
        for index, line in enumerate(lines):
            cls.draw_text(
                line,
                position=(text_x, text_top - line_h * index),
                size=size,
                color=text_color,
            )
        return (
            center_x - width * 0.5,
            bottom,
            center_x + width * 0.5,
            top,
        )

    @classmethod
    def draw_runtime_tooltip(
            cls,
            tooltip,
            *,
            anchor_rect,
            viewport_size,
            size,
            scale=1.0,
            fill=(0.055, 0.055, 0.055, 0.97),
            stroke=(0.28, 0.28, 0.28, 0.9),
            text_color=(0.92, 0.92, 0.92, 1.0),
            metadata_color=(0.56, 0.56, 0.56, 1.0),
            issue_color=(0.9, 0.35, 0.18, 1.0),
            reveal=1.0,
    ):
        """Draw a Blender-style metadata tooltip with a delayed fade-in."""
        if tooltip is None or anchor_rect is None:
            return None
        reveal = min(1.0, max(0.0, float(reveal)))
        if reveal <= 0.0:
            return None
        from .blf_text import measure_text, wrap_text

        def faded(color):
            value = tuple(color)
            if len(value) == 3:
                value = (*value, 1.0)
            return (*value[:3], value[3] * reveal)

        viewport_w, viewport_h = (float(value) for value in viewport_size)
        scale = max(0.5, float(scale))
        margin = max(6.0, 8.0 * scale)
        gap = max(4.0, 5.0 * scale)
        pad_x = max(8.0, 10.0 * scale)
        pad_y = max(6.0, 7.0 * scale)
        section_gap = max(3.0, 4.0 * scale)
        title_size = max(10.0, float(size))
        body_size = max(9.0, title_size * 0.94)
        metadata_size = max(8.0, title_size * 0.88)
        max_width = max(
            1.0,
            min(580.0 * scale, viewport_w - margin * 2.0),
        )
        text_max_width = max(1.0, max_width - pad_x * 2.0)
        entries = []

        def add_block(text, font_size, color, max_lines, *, block_gap=0.0):
            lines = wrap_text(
                text,
                text_max_width,
                font_size,
                max_lines=max_lines,
            )
            for index, line in enumerate(lines):
                entries.append((
                    line,
                    font_size,
                    color,
                    block_gap if index == 0 and entries else 0.0,
                ))

        add_block(tooltip.title, title_size, text_color, 2)
        if tooltip.description:
            add_block(
                tooltip.description,
                body_size,
                text_color,
                3,
                block_gap=section_gap,
            )
        if tooltip.details:
            for index, detail in enumerate(tooltip.details):
                add_block(
                    f"{detail.label}: {detail.value}",
                    metadata_size,
                    metadata_color,
                    2,
                    block_gap=section_gap if index == 0 else 0.0,
                )
        if tooltip.issues:
            for index, issue in enumerate(tooltip.issues):
                add_block(
                    f"! {issue}",
                    body_size,
                    issue_color,
                    2,
                    block_gap=section_gap if index == 0 else 0.0,
                )
        if not entries:
            return None

        content_width = max(
            measure_text(line, font_size)[0]
            for line, font_size, _color, _gap_before in entries
        )
        anchor_x1, anchor_y1, anchor_x2, anchor_y2 = (
            float(value) for value in anchor_rect
        )
        anchor_w = max(0.0, anchor_x2 - anchor_x1)
        width = min(
            max_width,
            max(content_width + pad_x * 2.0, min(anchor_w, max_width)),
        )
        height = pad_y * 2.0
        for _line, font_size, _color, gap_before in entries:
            height += gap_before + measure_text("Ag", font_size)[1]

        center_x = (anchor_x1 + anchor_x2) * 0.5
        center_x = min(
            viewport_w - margin - width * 0.5,
            max(margin + width * 0.5, center_x),
        )
        below_top = anchor_y1 - gap
        placed_below = below_top - height >= margin
        if placed_below:
            top = below_top
        elif anchor_y2 + gap + height <= viewport_h - margin:
            top = anchor_y2 + gap + height
        else:
            top = min(viewport_h - margin, max(margin + height, below_top))
        slide = max(0.0, 4.0 * scale * (1.0 - reveal))
        top += slide if placed_below else -slide
        bottom = top - height
        center_y = bottom + height * 0.5

        cls.draw_rounded_rectangle_outlined(
            (center_x, center_y),
            fill=faded(fill),
            stroke=faded(stroke),
            radius=min(4.0 * scale, height * 0.12),
            width=width,
            height=height,
            line_width=max(0.75, scale),
        )
        text_x = center_x - width * 0.5 + pad_x
        cursor_top = top - pad_y
        for line, font_size, color, gap_before in entries:
            cursor_top -= gap_before
            cls.draw_text(
                line,
                position=(text_x, cursor_top),
                size=font_size,
                color=faded(color),
            )
            cursor_top -= measure_text("Ag", font_size)[1]
        return (
            center_x - width * 0.5,
            bottom,
            center_x + width * 0.5,
            top,
        )

    @staticmethod
    def draw_2d_line(pos, color=(1.0, 1.0, 1.0, 1), line_width=1):
        draw_line(pos, color, line_width, is_cycle=False)

    @staticmethod
    def draw_rectangle(x, y, width, height, color=(0, 0, 0, 1.0)):
        x2, y2 = x + width, y + height
        PublicGpu.draw_2d_rectangle(x, y, x2, y2, color)

    @staticmethod
    def draw_2d_rectangle(x: int, y: int, x2: int, y2: int, color=(0, 0, 0, 1.0)):
        _ensure_alpha_blend()
        vertices = ((x, y), (x2, y), (x, y2), (x2, y2))
        indices = ((0, 1, 2), (2, 1, 3))
        shader = _get_shader('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        shader.bind()
        shader.uniform_float("color", _as_rgba(color))
        batch.draw(shader)

    @staticmethod
    def draw_circle(position, radius, *, color=(1, 1, 1, 1.0), line_width=2, segments=DEFAULT_CIRCLE_SEGMENTS):
        from math import pi, ceil, acos

        radius = float(radius)
        if segments is None:
            max_pixel_error = 0.25
            segments = int(ceil(pi / acos(1.0 - max_pixel_error / max(radius, 1e-6))))
            segments = max(segments, 8)
            segments = min(segments, 1000)

        if segments <= 0:
            raise ValueError("Amount of segments must be greater than 0.")

        # Bake radius into vertices. Custom stroke expands in *vertex* space; a
        # matrix scale would multiply line_width by radius (sunburst / huge ring).
        unit = from_segments_generator_circle_vertex(segments)
        verts = tuple((x * radius, y * radius) for x, y, *_ in unit)
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            draw_line(verts, color, line_width, is_cycle=True)

    @staticmethod
    def draw_arc(position, radius, angle, arc, color=(0.4, 0.3, 0.8, 1), line_width=2,
                 segments=DEFAULT_CIRCLE_SEGMENTS):
        """Draw an arc of ``arc`` degrees centered on compass ``angle`` (degrees)."""
        radius = float(radius)
        mid = math.radians(float(angle) - float(arc) * 0.5)
        cos_m = math.cos(mid)
        sin_m = math.sin(mid)
        # Rotate + scale in Python so stroke width stays in pixel units.
        verts = []
        for x, y in get_arc_vertex(arc, segments):
            xr = x * cos_m - y * sin_m
            yr = x * sin_m + y * cos_m
            verts.append((xr * radius, yr * radius))
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            draw_line(verts, color, line_width, is_cycle=False)

    @staticmethod
    def draw_rounded_rectangle_area(
            position, color=(1, 1, 1, 1.0), *, radius=10, width=200, height=200,
            segments=DEFAULT_ROUND_SEGMENTS,
            corner_mask=(True, True, True, True),
    ):
        r = _clamp_rounded_radius(radius, width, height)
        corner_mask = tuple(bool(value) for value in corner_mask)
        _draw_rounded_fill(position, color, r, width, height, segments, corner_mask)

    @staticmethod
    def draw_rounded_rectangle_outlined(
            position,
            fill=(1, 1, 1, 1.0),
            stroke=(0.45, 0.45, 0.45, 0.35),
            *,
            radius=10,
            width=200,
            height=200,
            line_width=0.8,
            segments=DEFAULT_ROUND_SEGMENTS,
            corner_mask=(True, True, True, True),
    ):
        """Flat filled rounded rect with a thin anti-aliased outline.

        Draw fill at full size first, then stroke on top. Insetting the fill
        under an AA stroke left corner gaps (panel chrome showing through).
        """
        if width <= 0 or height <= 0:
            return
        r = _clamp_rounded_radius(radius, width, height)
        lw = max(0.5, float(line_width))
        segs = _round_rect_segments(r, segments)
        corner_mask = tuple(bool(value) for value in corner_mask)
        # Full-size fill — stroke AA covers the hard triangle silhouette.
        _draw_rounded_fill(position, fill, r, width, height, segs, corner_mask)
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(r, width, height, segs, corner_mask)
            draw_line(vertex, stroke, line_width=lw, is_cycle=True)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        """Draw square point markers (GPU POINTS)."""
        if not points:
            return
        _ensure_alpha_blend()
        gpu.state.point_size_set(max(1.0, float(point_size)))
        shader = _point_shader()
        pos = [_as_vec3(p) for p in points]
        batch = batch_for_shader(shader, 'POINTS', {"pos": pos})
        shader.bind()
        try:
            shader.uniform_float("color", _as_rgba(color))
        except Exception:
            pass
        batch.draw(shader)
