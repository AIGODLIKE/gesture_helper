import math
from functools import cache

import blf
import bpy
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
    _GPU_DRAW_DEPTH = 0
    _SAVED_BLEND = None
    _SAVED_DEPTH_TEST = None
    try:
        from .gpu_stroke import clear_stroke_shader_cache
        clear_stroke_shader_cache()
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


@cache
def get_rounded_rectangle_vertex(radius=10, width=200, height=200, segments=12) -> tuple:
    """Outline vertices for a centered rounded rect (CCW, Y-up)."""
    if segments <= 0:
        raise ValueError("Amount of segments must be greater than 0.")
    radius = float(max(0.01, min(radius, width * 0.5, height * 0.5)))
    hw = width * 0.5 - radius
    hh = height * 0.5 - radius
    # Corner centers: TR, TL, BL, BR — each arc covers 90°.
    corners = (
        (hw, hh, 0.0),        # TR: 0 → 90
        (-hw, hh, 90.0),      # TL: 90 → 180
        (-hw, -hh, 180.0),    # BL: 180 → 270
        (hw, -hh, 270.0),     # BR: 270 → 360
    )
    vertex = []
    step = 90.0 / segments
    for cx, cy, start in corners:
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
def get_rounded_fill_mesh(radius, width, height, segments):
    """Center-fan mesh for a filled rounded rect."""
    outline = get_rounded_rectangle_vertex(radius, width, height, segments)
    verts = ((0.0, 0.0),) + outline
    n = len(outline)
    indices = tuple((0, i, i + 1) for i in range(1, n)) + ((0, n, 1),)
    return verts, indices


def _rounded_radius(radius):
    scale = bpy.context.preferences.view.ui_scale
    from .public import get_pref
    margin = min(get_pref().draw_property.margin) * scale
    return min(float(radius), float(margin))


def _get_rounded_fill_batch(radius, width, height, segments):
    key = (round(radius, 3), round(width, 3), round(height, 3), int(segments))
    shader = _get_shader('UNIFORM_COLOR')
    entry = _ROUNDED_FILL_BATCH.get(key)
    if entry is not None and entry[0] is shader:
        return entry[1]
    verts, indices = get_rounded_fill_mesh(radius, width, height, segments)
    batch = batch_for_shader(shader, 'TRIS', {"pos": verts}, indices=indices)
    _ROUNDED_FILL_BATCH[key] = (shader, batch)
    return batch


def _draw_rounded_fill(position, color, radius, width, height, segments):
    if width <= 0 or height <= 0:
        return
    r = min(float(radius), width * 0.5, height * 0.5)
    _ensure_alpha_blend()
    shader = _get_shader('UNIFORM_COLOR')
    batch = _get_rounded_fill_batch(r, width, height, segments)
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
            auto_offset=False,
    ):
        from . import including_chinese
        with gpu.matrix.push_pop():
            if including_chinese(text) and auto_offset:
                (_w, height) = blf.dimensions(font_id, text)
                gpu.matrix.translate([0, -height * .075])

            x, y = position
            blf.disable(font_id, blf.CLIPPING)
            blf.disable(font_id, blf.MONOCHROME)
            blf.size(font_id, size)
            blf.color(font_id, *color)
            blf.position(font_id, x, y - (size * (column + 1)), z)
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
    ):
        r = _rounded_radius(radius)
        _draw_rounded_fill(position, color, r, width, height, segments)

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
    ):
        """Flat filled rounded rect with a thin anti-aliased outline."""
        r = _rounded_radius(radius)
        lw = max(0.5, float(line_width))
        # Inset fill so the AA stroke covers hard triangle edges.
        inset = min(lw * 0.5, r * 0.35, width * 0.25, height * 0.25)
        fill_w = max(1.0, width - inset * 2)
        fill_h = max(1.0, height - inset * 2)
        fill_r = max(0.01, r - inset)
        _draw_rounded_fill(position, fill, fill_r, fill_w, fill_h, segments)
        with gpu.matrix.push_pop():
            gpu.matrix.translate(position)
            vertex = get_rounded_rectangle_vertex(r, width, height, segments)
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
