"""Thick AA polyline with round joins/caps (gap-less at sharp corners).

Problem: per-segment quads (Blender POLYLINE / butt joins) leave wedges at
sharp turns. The common fix used by SVG, Canvas, ImGui and GPU line libs is
**round joins**: a disc of radius ``half_width`` at every vertex fills the
outer wedge so the stroke never breaks.

AA matches Blender's POLYLINE fringe:

    alpha *= clamp(half - dist, 0, 1)

where ``dist`` is the distance from the stroke centerline / join center
(``length(lineCoord)``).
"""

from __future__ import annotations

import math

import gpu
from gpu_extras.batch import batch_for_shader

SMOOTH_WIDTH = 1.0
# Segments for round join / cap discs (more = smoother elbows).
JOIN_SEGMENTS = 16

_STROKE_SHADER = None
_STROKE_SHADER_FAILED = False

_VERT = """
void main()
{
    vLineCoord = lineCoord;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}
"""

_FRAG = """
void main()
{
    /* Radial distance from stroke center (strip: |y|; join/cap: length). */
    float dist = length(vLineCoord);
    float half_width = (lineWidth + SMOOTH_WIDTH) * 0.5;
    vec4 col = color;
    col.a *= clamp(half_width - dist, 0.0, 1.0);
    fragColor = col;
}
"""


def _create_stroke_shader():
    vert_out = gpu.types.GPUStageInterfaceInfo("GestureStrokeIface")
    vert_out.no_perspective("VEC2", "vLineCoord")

    info = gpu.types.GPUShaderCreateInfo()
    info.define("SMOOTH_WIDTH", "1.0")
    info.push_constant("MAT4", "ModelViewProjectionMatrix")
    info.push_constant("VEC4", "color")
    info.push_constant("FLOAT", "lineWidth")
    info.vertex_in(0, "VEC2", "pos")
    info.vertex_in(1, "VEC2", "lineCoord")
    info.vertex_out(vert_out)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_VERT)
    info.fragment_source(_FRAG)
    shader = gpu.shader.create_from_info(info)
    shader._gesture_iface = vert_out  # type: ignore[attr-defined]
    return shader


def get_stroke_shader():
    global _STROKE_SHADER, _STROKE_SHADER_FAILED
    if _STROKE_SHADER is not None:
        return _STROKE_SHADER
    if _STROKE_SHADER_FAILED:
        return None
    try:
        _STROKE_SHADER = _create_stroke_shader()
    except Exception as exc:
        if "background" in str(exc).lower():
            return None
        _STROKE_SHADER_FAILED = True
        return None
    return _STROKE_SHADER


def clear_stroke_shader_cache():
    global _STROKE_SHADER, _STROKE_SHADER_FAILED
    _STROKE_SHADER = None
    _STROKE_SHADER_FAILED = False


def _as_xy(v):
    return float(v[0]), float(v[1])


def _emit_round_disc(
        pos: list,
        coords: list,
        indices: list,
        cx: float,
        cy: float,
        half: float,
        segments: int,
) -> None:
    """Triangle fan disc used as round join / round cap."""
    base = len(pos)
    pos.append((cx, cy))
    coords.append((0.0, 0.0))
    for i in range(segments + 1):
        a = (math.tau * i) / segments
        c = math.cos(a)
        s = math.sin(a)
        pos.append((cx + c * half, cy + s * half))
        coords.append((c * half, s * half))
    for i in range(segments):
        indices.append((base, base + 1 + i, base + 2 + i))


def build_polyline_mesh(
        points,
        line_width: float,
        *,
        is_cycle: bool = False,
        join_segments: int = JOIN_SEGMENTS,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[int, int, int]]] | None:
    """Build segment quads + round joins/caps (no gaps at sharp corners)."""
    if not points or len(points) < 2:
        return None

    pts = [_as_xy(p) for p in points]
    if is_cycle and pts[0] != pts[-1]:
        pts.append(pts[0])

    # Drop zero-length consecutive duplicates (keeps join math stable).
    cleaned = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 1e-4:
            cleaned.append(p)
    if is_cycle and len(cleaned) >= 2:
        if math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) > 1e-4:
            cleaned.append(cleaned[0])
    pts = cleaned
    if len(pts) < 2:
        return None

    lw = max(1.0, float(line_width))
    half = (lw + SMOOTH_WIDTH) * 0.5
    segs = max(8, int(join_segments))

    pos: list[tuple[float, float]] = []
    coords: list[tuple[float, float]] = []
    indices: list[tuple[int, int, int]] = []

    count = len(pts)
    # Open path: last point is endpoint; closed path with duplicated first: skip last for joins.
    if is_cycle and count >= 3 and pts[0] == pts[-1]:
        body = count - 1
    else:
        body = count

    # --- segment quads (butt ends) ---
    seg_n = body if is_cycle else (body - 1)
    for i in range(seg_n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % body] if is_cycle else pts[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        ex = dx / length
        ey = dy / length
        ox = -ey * half
        oy = ex * half

        base = len(pos)
        # lineCoord.y = signed distance across stroke (Blender smoothline).
        pos.append((x0 + ox, y0 + oy))
        coords.append((0.0, half))
        pos.append((x0 - ox, y0 - oy))
        coords.append((0.0, -half))
        pos.append((x1 + ox, y1 + oy))
        coords.append((0.0, half))
        pos.append((x1 - ox, y1 - oy))
        coords.append((0.0, -half))
        indices.append((base + 0, base + 1, base + 2))
        indices.append((base + 1, base + 3, base + 2))

    # --- round joins at every vertex (open ends become round caps) ---
    for i in range(body):
        x, y = pts[i]
        _emit_round_disc(pos, coords, indices, x, y, half, segs)

    if not indices:
        return None
    return pos, coords, indices


def draw_smooth_stroke(points, color, line_width: float, *, is_cycle: bool = False, smooth: bool = True) -> bool:
    """Draw a gap-less AA stroke with round joins. Returns False to request fallback."""
    del smooth  # kept for call-site compatibility
    shader = get_stroke_shader()
    if shader is None:
        return False

    lw = max(1.0, float(line_width))
    mesh = build_polyline_mesh(points, lw, is_cycle=is_cycle)
    if mesh is None:
        return True

    pos, line_coords, indices = mesh
    gpu.state.blend_set("ALPHA")
    batch = batch_for_shader(
        shader,
        "TRIS",
        {"pos": pos, "lineCoord": line_coords},
        indices=indices,
    )
    shader.bind()
    mvp = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    shader.uniform_float("ModelViewProjectionMatrix", mvp)
    c = tuple(color)
    if len(c) == 3:
        c = (c[0], c[1], c[2], 1.0)
    shader.uniform_float("color", c)
    shader.uniform_float("lineWidth", lw)
    batch.draw(shader)
    return True


def draw_blender_polyline(points, color, line_width: float, *, is_cycle: bool = False) -> bool:
    """Fallback: built-in POLYLINE (still has butt-join gaps at sharp corners)."""
    if not points or len(points) < 2:
        return True

    pts = [_as_xy(p) for p in points]
    if is_cycle and pts[0] != pts[-1]:
        pts.append(pts[0])

    paired = []
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        paired.append((x0, y0, 0.0))
        paired.append((x1, y1, 0.0))
    if len(paired) < 2:
        return True

    try:
        shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    except Exception:
        return False

    import bpy
    region = getattr(bpy.context, "region", None)
    if region is not None:
        viewport = (float(region.width), float(region.height))
    else:
        viewport = tuple(float(v) for v in gpu.state.viewport_get()[2:])

    c = tuple(color)
    if len(c) == 3:
        c = (c[0], c[1], c[2], 1.0)

    gpu.state.blend_set("ALPHA")
    batch = batch_for_shader(shader, "LINES", {"pos": paired})
    shader.bind()
    shader.uniform_float("viewportSize", viewport)
    shader.uniform_float("lineWidth", max(1.0, float(line_width)))
    shader.uniform_float("color", c)
    batch.draw(shader)
    return True
