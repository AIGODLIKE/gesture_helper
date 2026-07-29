"""Retained overlay layout for the gesture-preview HUD.

Replaces the legacy ``bpu`` widget tree. The layout is measured once per
content change, arranged in window coordinates, and all panel / row chrome is
submitted as a single GPU batch. Rounded corners and anti-aliasing come from a
custom SDF shader (``GPUShaderCreateInfo``, backend-agnostic); text remains a
separate BLF pass, as required by Blender.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ...utils.public_gpu import gpu_draw_begin, gpu_draw_end

_VERT_SRC = """
void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
    finalColor = color;
    fragPos = pos;
    rectData = rect;
    cornerRadius = radius;
}
"""

# Rounded-box SDF: rectData = (center_x, center_y, half_w, half_h) in region px.
# fragPos is interpolated in the same space, so no gl_FragCoord assumptions.
_FRAG_SRC = """
/* Match builtin overlay shaders: IEC sRGB uniform -> linear framebuffer. */
vec4 gesture_srgb_to_framebuffer_space(vec4 in_color)
{
    vec3 c = max(in_color.rgb, vec3(0.0));
    vec3 c1 = c * (1.0 / 12.92);
    vec3 c2 = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
    in_color.rgb = mix(c1, c2, step(vec3(0.04045), c));
    return in_color;
}

void main()
{
    vec2 p = fragPos - rectData.xy;
    vec2 b = rectData.zw;
    float r = min(cornerRadius, min(b.x, b.y));
    vec2 q = abs(p) - (b - vec2(r));
    float d = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - r;
    float alpha = 1.0 - smoothstep(-0.75, 0.75, d);
    vec4 col = gesture_srgb_to_framebuffer_space(finalColor);
    col.a *= alpha;
    fragColor = col;
}
"""

_shader = None
_shader_failed = False


def _rounded_rect_shader():
    """Create (once) the batched rounded-rect shader; None if unsupported."""
    global _shader, _shader_failed
    if _shader is not None or _shader_failed:
        return _shader
    try:
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "ModelViewProjectionMatrix")
        info.vertex_in(0, 'VEC2', "pos")
        info.vertex_in(1, 'VEC4', "color")
        info.vertex_in(2, 'VEC4', "rect")
        info.vertex_in(3, 'FLOAT', "radius")
        iface = gpu.types.GPUStageInterfaceInfo("gh_overlay_rrect_iface")
        iface.smooth('VEC4', "finalColor")
        iface.smooth('VEC2', "fragPos")
        iface.flat('VEC4', "rectData")
        iface.flat('FLOAT', "cornerRadius")
        info.vertex_out(iface)
        info.fragment_out(0, 'VEC4', "fragColor")
        info.vertex_source(_VERT_SRC)
        info.fragment_source(_FRAG_SRC)
        _shader = gpu.shader.create_from_info(info)
    except Exception:
        _shader_failed = True
    return _shader


def clear_overlay_shader():
    """Drop the cached shader (reload-safe)."""
    global _shader, _shader_failed
    _shader = None
    _shader_failed = False


@dataclass
class OverlayNode:
    kind: str
    text: str = ""
    tooltip: str = ""
    active: bool = False
    alert: bool = False
    operator: str = ""
    properties: SimpleNamespace | None = None
    data: object | None = None
    prop: str = ""
    draggable: bool = False
    fill_width: bool = False
    align_last: bool = False
    alpha_multiplier: float = 1.0
    children: list["OverlayNode"] = field(default_factory=list)
    # (x1, y1, x2, y2) in window coordinates after arrange.
    rect: tuple[float, float, float, float] | None = None
    size: Vector = field(default_factory=lambda: Vector((0.0, 0.0)))


class _RectBatch:
    """Collect rounded rects, then draw them all in one call."""

    __slots__ = ("pos", "color", "rect", "radius", "indices", "_gpu_batch", "_use_sdf")

    def __init__(self):
        self.pos = []
        self.color = []
        self.rect = []
        self.radius = []
        self.indices = []
        self._gpu_batch = None
        self._use_sdf = True

    def add(self, x1, y1, x2, y2, color, radius):
        base = len(self.pos)
        self.pos.extend(((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
        self.color.extend((color,) * 4)
        cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        hw, hh = (x2 - x1) * 0.5, (y2 - y1) * 0.5
        self.rect.extend(((cx, cy, hw, hh),) * 4)
        self.radius.extend((radius,) * 4)
        self.indices.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))

    def build(self):
        """Compile GPU batch once; safe to call again after content changes."""
        self._gpu_batch = None
        if not self.pos:
            return
        shader = _rounded_rect_shader()
        if shader is not None:
            self._use_sdf = True
            self._gpu_batch = batch_for_shader(
                shader, 'TRIS',
                {"pos": self.pos, "color": self.color, "rect": self.rect, "radius": self.radius},
                indices=self.indices,
            )
            return
        self._use_sdf = False
        fallback = gpu.shader.from_builtin('SMOOTH_COLOR')
        self._gpu_batch = batch_for_shader(
            fallback, 'TRIS', {"pos": self.pos, "color": self.color}, indices=self.indices,
        )

    def draw(self):
        if not self.pos:
            return
        if self._gpu_batch is None:
            self.build()
        if self._gpu_batch is None:
            return
        try:
            if self._use_sdf:
                shader = _rounded_rect_shader()
                if shader is None:
                    # Shader dropped after reload — rebuild via fallback next call.
                    self._gpu_batch = None
                    self.build()
                    if self._gpu_batch is None:
                        return
                    if self._use_sdf:
                        shader = _rounded_rect_shader()
                if shader is not None and self._use_sdf:
                    shader.bind()
                    matrix = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
                    shader.uniform_float("ModelViewProjectionMatrix", matrix)
                    self._gpu_batch.draw(shader)
                    return
            fallback = gpu.shader.from_builtin('SMOOTH_COLOR')
            fallback.bind()
            self._gpu_batch.draw(fallback)
        except Exception:
            # Stale batch after addon reload / GPU context loss.
            self._gpu_batch = None
            self.build()
            if self._gpu_batch is None:
                return
            if self._use_sdf:
                shader = _rounded_rect_shader()
                if shader is not None:
                    shader.bind()
                    matrix = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
                    shader.uniform_float("ModelViewProjectionMatrix", matrix)
                    self._gpu_batch.draw(shader)
                    return
            fallback = gpu.shader.from_builtin('SMOOTH_COLOR')
            fallback.bind()
            self._gpu_batch.draw(fallback)


class OverlayLayout:
    """Blender-like row/column/box overlay with operator/property rows.

    Coordinates: ``offset_position`` and ``mouse_position`` are window pixels
    (``event.mouse_x/y``); the draw pass converts to region pixels itself.
    """

    def __init__(self):
        self.root = OverlayNode("COLUMN")
        self._stack = [self.root]
        self.offset_position = Vector((0.0, 0.0))
        self.mouse_position = Vector((-1e6, -1e6))
        # 'TOP_LEFT' | 'RIGHT_CENTER' | 'TOP_LEFT_REGION' | 'BOTTOM_LEFT_REGION'
        self.anchor = 'TOP_LEFT'
        self.root_draggable = False
        self.font_size = 14
        self.padding = 7
        self.min_row_height = 24
        self.gap = 3
        self.corner_radius = 6
        self.background = (0.10, 0.10, 0.10, 0.92)
        self.row_color = (0.22, 0.22, 0.22, 0.9)
        self.header_color = (0.16, 0.17, 0.19, 0.96)
        self.hover_color = (0.28, 0.45, 0.75, 0.95)
        self.pressed_color = (0.10, 0.24, 0.52, 0.98)
        self.active_color = (0.20, 0.38, 0.65, 0.95)
        self.alert_color = (0.48, 0.12, 0.12, 0.95)
        self.text_color = (0.92, 0.92, 0.92, 1.0)
        self.text_hover_color = (1.0, 1.0, 1.0, 1.0)
        self.alert_text_color = (1.0, 0.45, 0.45, 1.0)
        self.separator_color = (1.0, 1.0, 1.0, 0.15)
        self._hover = None
        self._pressed = None
        self._laid_out = False
        self._content_gen = 0
        self._cached_rects: _RectBatch | None = None
        self._cached_batch_sig = None
        self._theme_signature = None
        self.interaction_revision = 0
        self.drag_offset = Vector((0.0, 0.0))
        self._base_offset_position = Vector((0.0, 0.0))
        self._drag_mouse = None
        self.drag_revision = 0

    # ---- build API (with-statement rebuilds content) ----

    def __enter__(self):
        if self._pressed is not None:
            self._pressed = None
            self.interaction_revision += 1
        self.root.children.clear()
        self._stack[:] = [self.root]
        self._laid_out = False
        self._content_gen += 1
        self._cached_batch_sig = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._laid_out = False
        self._cached_batch_sig = None

    def _add(self, node):
        self._stack[-1].children.append(node)
        return node

    def label(self, text="", alert=False, draggable=False):
        return self._add(OverlayNode(
            "LABEL",
            text=str(text),
            alert=alert,
            draggable=draggable,
        ))

    def separator(self):
        return self._add(OverlayNode("SEPARATOR"))

    def operator(
            self,
            operator,
            text=None,
            active=False,
            *,
            tooltip="",
            fill_width=False,
            alpha_multiplier=1.0,
    ):
        props = SimpleNamespace()
        self._add(OverlayNode(
            "OPERATOR",
            text=text or operator,
            tooltip=str(tooltip),
            active=active,
            operator=operator,
            properties=props,
            fill_width=bool(fill_width),
            alpha_multiplier=max(0.0, float(alpha_multiplier)),
        ))
        return props

    def prop(self, data, prop, text=None):
        label = text or data.bl_rna.properties[prop].name
        return self._add(OverlayNode("PROPERTY", text=label, data=data, prop=prop))

    def _container(self, kind, *, fill_width=False, align_last=False):
        node = self._add(OverlayNode(
            kind,
            fill_width=bool(fill_width),
            align_last=bool(align_last),
        ))
        return _LayoutScope(self, node)

    def row(self, *, fill_width=False, align_last=False):
        return self._container(
            "ROW",
            fill_width=fill_width,
            align_last=align_last,
        )

    def column(self):
        return self._container("COLUMN")

    def box(self):
        return self._container("BOX")

    # ---- layout ----

    def _node_text(self, node) -> str:
        if node.kind == "PROPERTY":
            return f"{node.text}: {getattr(node.data, node.prop)}"
        return node.text

    def _measure(self, node):
        if node.kind in {"LABEL", "OPERATOR", "PROPERTY"}:
            from ...utils.blf_text import measure_text
            w, line_h = measure_text(self._node_text(node), self.font_size)
            node.size = Vector((
                w + self.padding * 2,
                max(line_h + self.padding * 2, self.min_row_height),
            ))
        elif node.kind == "SEPARATOR":
            node.size = Vector((16, 7))
        else:
            sizes = [self._measure(child) for child in node.children]
            if not sizes:
                node.size = Vector((0, 0))
            elif node.kind == "ROW":
                node.size = Vector((
                    sum(s.x for s in sizes) + self.gap * (len(sizes) - 1),
                    max(s.y for s in sizes),
                ))
            else:
                node.size = Vector((
                    max(s.x for s in sizes),
                    sum(s.y for s in sizes) + self.gap * (len(sizes) - 1),
                ))
            if node.kind == "BOX":
                node.size += Vector((self.padding * 2, self.padding * 2))
        return node.size

    def _arrange(self, node, x, y):
        node.rect = (x, y - node.size.y, x + node.size.x, y)
        if node.kind not in {"ROW", "COLUMN", "BOX"}:
            return
        inset = self.padding if node.kind == "BOX" else 0
        cx, cy = x + inset, y - inset
        for child in node.children:
            self._arrange(child, cx, cy)
            if (
                    node.kind in {'COLUMN', 'BOX'}
                    and (child.draggable or child.fill_width)
            ):
                x1, y1, _x2, y2 = child.rect
                child.rect = (x1, y1, x + node.size.x - inset, y2)
                if child.kind == "ROW" and child.align_last and child.children:
                    trailing = child.children[-1]
                    delta_x = child.rect[2] - trailing.rect[2]
                    if delta_x > 0.0:
                        self._translate_node(trailing, delta_x, 0.0)
            if node.kind == "ROW":
                cx += child.size.x + self.gap
            else:
                cy -= child.size.y + self.gap

    def _translate_node(self, node, dx, dy):
        if node.rect is not None:
            x1, y1, x2, y2 = node.rect
            node.rect = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        for child in node.children:
            self._translate_node(child, dx, dy)

    def _walk(self, node=None):
        node = node or self.root
        for child in node.children:
            yield child
            yield from self._walk(child)

    def _anchor_origin(self) -> Vector:
        w, h = self.root.size
        x, y = self.offset_position
        if self.anchor == 'RIGHT_CENTER':
            return Vector((x - w, y + h / 2))
        if self.anchor == 'TOP_LEFT_REGION':
            region = bpy.context.region
            pad = self.padding * 2
            if region is not None:
                return Vector((
                    region.x + pad + x,
                    region.y + region.height - pad + y,
                ))
            return Vector((pad + x, pad + y))
        if self.anchor == 'BOTTOM_LEFT_REGION':
            region = bpy.context.region
            pad = self.padding * 2
            if region is not None:
                return Vector((region.x + pad + x, region.y + pad + h + y))
            return Vector((pad + x, pad + h + y))
        return Vector((x, y))

    def sync_input(self, offset, mouse):
        """Update anchor/mouse (window px).

        Offset changes invalidate measure/arrange. Mouse-only moves only
        recompute hover (point-in-rect), keeping layout geometry cached.
        """
        base_offset = Vector(offset)
        offset = base_offset + self.drag_offset
        mouse = Vector(mouse) if mouse is not None else Vector((-1e6, -1e6))
        self._base_offset_position = base_offset
        offset_changed = offset != self.offset_position
        mouse_changed = mouse != self.mouse_position
        if not offset_changed and not mouse_changed:
            return False
        self.offset_position = offset
        self.mouse_position = mouse
        if offset_changed:
            self._laid_out = False
            self._cached_batch_sig = None
            return False
        if self._laid_out:
            prev = self._hover
            self._update_hover()
            if self._hover is not prev:
                self._cached_batch_sig = None
                return True
        return False

    def _update_hover(self):
        mouse = self.mouse_position
        self._hover = next(
            (n for n in self._walk()
             if n.kind in {"OPERATOR", "PROPERTY"} and self._contains(n.rect, mouse)),
            None,
        )

    @property
    def hover_tooltip(self) -> str:
        node = self._hover
        if node is None:
            return ""
        return str(node.tooltip or "")

    def _ensure_layout(self):
        if self._laid_out:
            return
        self._measure(self.root)
        origin = self._anchor_origin()
        self._arrange(self.root, origin.x, origin.y)
        self._update_hover()
        self._laid_out = True
        self._cached_batch_sig = None

    @staticmethod
    def _contains(rect, point):
        return bool(rect and rect[0] <= point.x <= rect[2] and rect[1] <= point.y <= rect[3])

    # ---- draw ----

    def _sync_theme(self) -> None:
        """Resolve the add-on palette once per actual preference change."""
        try:
            from ...utils.public import get_pref

            draw = get_pref().draw_property
            raw = (
                tuple(draw.overlay_background_color),
                tuple(draw.background_operator_color),
                tuple(draw.overlay_header_color),
                tuple(draw.interaction_hover_color),
                tuple(draw.interaction_pressed_color),
                tuple(draw.background_operator_active_color),
                tuple(draw.status_error_color),
                tuple(draw.text_default_color),
                tuple(draw.text_active_color),
                tuple(draw.dividing_line_color),
            )
        except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError):
            return
        if raw == self._theme_signature:
            return
        from ...utils.color import color_to_gpu, color_to_srgb

        (
            panel,
            row,
            header,
            hover,
            pressed,
            active,
            alert,
            text,
            text_hover,
            separator,
        ) = raw
        self.background = color_to_gpu(panel)
        self.row_color = color_to_gpu(row)
        self.header_color = color_to_gpu(header)
        self.hover_color = color_to_gpu(hover)
        self.pressed_color = color_to_gpu(pressed)
        self.active_color = color_to_gpu(active)
        self.alert_color = color_to_gpu(alert)
        self.text_color = color_to_srgb(text)
        self.text_hover_color = color_to_srgb(text_hover)
        self.alert_text_color = color_to_srgb(alert)
        self.separator_color = color_to_gpu(separator)
        self._theme_signature = raw
        self._cached_batch_sig = None

    def _node_fill(self, node):
        if node is self._pressed and node is self._hover:
            return self.pressed_color
        if node is self._hover:
            return self.hover_color
        if node.draggable:
            return self.header_color
        if node.active:
            return self.active_color
        if node.alert and node.kind != "LABEL":
            return self.alert_color
        if node.kind in {"OPERATOR", "PROPERTY"}:
            return (
                *self.row_color[:3],
                self.row_color[3] * node.alpha_multiplier,
            )
        return self.background

    def _tooltip_geometry(self):
        node = self._hover
        text = self.hover_tooltip
        if not text or node is None or node.rect is None:
            return None
        from ...utils.blf_text import measure_text

        font_size = max(11.0, self.font_size * 0.9)
        text_width, line_height = measure_text(text, font_size)
        pad = max(4.0, self.padding)
        width = text_width + pad * 2.0
        height = line_height + pad * 2.0
        gap = max(4.0, self.gap)
        x2 = node.rect[2]
        x1 = x2 - width
        y1 = node.rect[3] + gap
        y2 = y1 + height

        region = bpy.context.region
        if region is not None:
            left = float(region.x) + 2.0
            right = float(region.x + region.width) - 2.0
            bottom = float(region.y) + 2.0
            top = float(region.y + region.height) - 2.0
            if y2 > top:
                y2 = node.rect[1] - gap
                y1 = y2 - height
            if x1 < left:
                x1 = left
                x2 = min(right, x1 + width)
            elif x2 > right:
                x2 = right
                x1 = max(left, x2 - width)
            if y1 < bottom:
                y1 = bottom
                y2 = min(top, y1 + height)
        return text, font_size, pad, line_height, (x1, y1, x2, y2)

    def _build_rect_batch(self, ox, oy) -> _RectBatch:
        rects = _RectBatch()
        root = self.root
        if root.rect is not None:
            x1, y1, x2, y2 = root.rect
            pad = self.padding
            rects.add(x1 - pad - ox, y1 - pad - oy, x2 + pad - ox, y2 + pad - oy,
                      self.background, self.corner_radius + pad * 0.5)
        for node in self._walk():
            if node.rect is None:
                continue
            x1, y1, x2, y2 = node.rect
            if node.kind == "SEPARATOR":
                mid = (y1 + y2) * 0.5
                w = max(root.size.x, x2 - x1)
                rects.add(x1 - ox, mid - 0.75 - oy, x1 + w - ox, mid + 0.75 - oy,
                          self.separator_color, 0.75)
                continue
            if node.kind not in {"OPERATOR", "PROPERTY", "BOX"} and not node.draggable:
                continue
            rects.add(x1 - ox, y1 - oy, x2 - ox, y2 - oy,
                      self._node_fill(node), self.corner_radius)
        tooltip = self._tooltip_geometry()
        if tooltip is not None:
            _text, _font_size, _pad, _line_height, (x1, y1, x2, y2) = tooltip
            rects.add(
                x1 - ox,
                y1 - oy,
                x2 - ox,
                y2 - oy,
                self.header_color,
                self.corner_radius,
            )
        rects.build()
        return rects

    def _batch_signature(self, ox, oy):
        hover_key = id(self._hover) if self._hover is not None else 0
        pressed_key = id(self._pressed) if self._pressed is not None else 0
        root_rect = self.root.rect
        tooltip = self._tooltip_geometry()
        return (
            self._content_gen,
            root_rect,
            hover_key,
            pressed_key,
            ox,
            oy,
            self.background,
            self.row_color,
            self.header_color,
            self.hover_color,
            self.pressed_color,
            self.active_color,
            self.alert_color,
            self.separator_color,
            self.corner_radius,
            self.padding,
            tooltip,
        )

    def __gpu_draw__(self):
        if not self.root.children:
            return
        self._sync_theme()
        self._ensure_layout()
        region = bpy.context.region
        ox = region.x if region is not None else 0
        oy = region.y if region is not None else 0

        sig = self._batch_signature(ox, oy)
        if self._cached_batch_sig != sig or self._cached_rects is None:
            self._cached_rects = self._build_rect_batch(ox, oy)
            self._cached_batch_sig = sig

        gpu_draw_begin()
        try:
            self._cached_rects.draw()
            from ...utils.blf_text import line_metrics
            ascent, _descent, line_h = line_metrics(self.font_size)
            blf.size(0, self.font_size)
            for node in self._walk():
                if node.kind not in {"LABEL", "OPERATOR", "PROPERTY"} or node.rect is None:
                    continue
                if node.alert and node.kind == "LABEL":
                    blf.color(0, *self.alert_text_color)
                elif node is self._hover or node.active:
                    blf.color(0, *self.text_hover_color)
                else:
                    blf.color(0, *self.text_color)
                # Center the metric line box in the row, baseline = top - ascent.
                x1, y1, _x2, y2 = node.rect
                baseline = y2 - (node.size.y - line_h) * 0.5 - ascent
                blf.position(0, x1 + self.padding - ox, baseline - oy, 0)
                blf.draw(0, self._node_text(node))
            tooltip = self._tooltip_geometry()
            if tooltip is not None:
                text, font_size, pad, line_h, (x1, y1, _x2, y2) = tooltip
                ascent, _descent, _metric_h = line_metrics(font_size)
                blf.size(0, font_size)
                blf.color(0, *self.text_hover_color)
                baseline = y2 - (y2 - y1 - line_h) * 0.5 - ascent
                blf.position(0, x1 + pad - ox, baseline - oy, 0)
                blf.draw(0, text)
        finally:
            gpu_draw_end()

    # ---- events ----

    def check_event(self, event) -> bool:
        """Handle one modal event. True when the overlay consumed it."""
        if not self.root.children:
            return False
        self._ensure_layout()
        if self._drag_mouse is not None:
            if event.type == 'MOUSEMOVE':
                mouse = Vector((event.mouse_x, event.mouse_y))
                diff = mouse - self._drag_mouse
                if diff.length_squared > 0.0:
                    self.drag_offset += diff
                    self.offset_position = self._base_offset_position + self.drag_offset
                    self.mouse_position = mouse
                    self._drag_mouse = mouse
                    self._laid_out = False
                    self._cached_batch_sig = None
                    self.drag_revision += 1
                return True
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self._drag_mouse = None
                return True
            return event.type == 'LEFTMOUSE'

        if self._pressed is not None:
            if event.type == 'MOUSEMOVE':
                return True
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                node = self._pressed
                activate = node is self._hover
                self._pressed = None
                self._cached_batch_sig = None
                self.interaction_revision += 1
                if not activate:
                    return True
                if node.kind == "PROPERTY":
                    value = getattr(node.data, node.prop)
                    if isinstance(value, bool):
                        setattr(node.data, node.prop, not value)
                    return True
                if node.kind == "OPERATOR" and '.' in node.operator:
                    module, name = node.operator.split('.', 1)
                    func = getattr(getattr(bpy.ops, module, None), name, None)
                    if func is not None:
                        func('INVOKE_DEFAULT', **vars(node.properties))
                return True
            if event.value == 'PRESS' and event.type in {'ESC', 'RIGHTMOUSE'}:
                self._pressed = None
                self._cached_batch_sig = None
                self.interaction_revision += 1
            return event.type == 'LEFTMOUSE'

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            header = next(
                (
                    node
                    for node in self._walk()
                    if node.draggable and self._contains(node.rect, self.mouse_position)
                ),
                None,
            )
            if header is not None:
                self._drag_mouse = Vector((event.mouse_x, event.mouse_y))
                return True
            if (
                    self.root_draggable
                    and self._hover is None
                    and self.root.rect is not None
            ):
                x1, y1, x2, y2 = self.root.rect
                pad = self.padding
                root_surface = (x1 - pad, y1 - pad, x2 + pad, y2 + pad)
                if self._contains(root_surface, self.mouse_position):
                    self._drag_mouse = Vector((event.mouse_x, event.mouse_y))
                    return True

        node = self._hover
        if node is None:
            return False
        # Hovering the selector must not block preview navigation or the
        # space-drag used to reposition the gesture. Only own the left-click
        # sequence that activates a row.
        if event.type != 'LEFTMOUSE':
            return False
        if event.value == 'PRESS':
            self._pressed = node
            self._cached_batch_sig = None
            self.interaction_revision += 1
            return True
        return event.value != 'RELEASE'


class _LayoutScope:
    def __init__(self, layout, node):
        self.layout, self.node = layout, node

    def __enter__(self):
        self.layout._stack.append(self.node)
        return self.layout

    def __exit__(self, exc_type, exc_value, traceback):
        self.layout._stack.pop()
