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
void main()
{
    vec2 p = fragPos - rectData.xy;
    vec2 b = rectData.zw;
    float r = min(cornerRadius, min(b.x, b.y));
    vec2 q = abs(p) - (b - vec2(r));
    float d = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - r;
    float alpha = 1.0 - smoothstep(-0.75, 0.75, d);
    fragColor = vec4(finalColor.rgb, finalColor.a * alpha);
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
    active: bool = False
    alert: bool = False
    operator: str = ""
    properties: SimpleNamespace | None = None
    data: object | None = None
    prop: str = ""
    children: list["OverlayNode"] = field(default_factory=list)
    # (x1, y1, x2, y2) in window coordinates after arrange.
    rect: tuple[float, float, float, float] | None = None
    size: Vector = field(default_factory=lambda: Vector((0.0, 0.0)))


class _RectBatch:
    """Collect rounded rects, then draw them all in one call."""

    def __init__(self):
        self.pos = []
        self.color = []
        self.rect = []
        self.radius = []
        self.indices = []

    def add(self, x1, y1, x2, y2, color, radius):
        base = len(self.pos)
        self.pos.extend(((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
        self.color.extend((color,) * 4)
        cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        hw, hh = (x2 - x1) * 0.5, (y2 - y1) * 0.5
        self.rect.extend(((cx, cy, hw, hh),) * 4)
        self.radius.extend((radius,) * 4)
        self.indices.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))

    def draw(self):
        if not self.pos:
            return
        shader = _rounded_rect_shader()
        if shader is not None:
            batch = batch_for_shader(
                shader, 'TRIS',
                {"pos": self.pos, "color": self.color, "rect": self.rect, "radius": self.radius},
                indices=self.indices,
            )
            shader.bind()
            matrix = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
            shader.uniform_float("ModelViewProjectionMatrix", matrix)
            batch.draw(shader)
            return
        # Fallback: flat-color triangles (no rounding) on exotic backends.
        fallback = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch = batch_for_shader(
            fallback, 'TRIS', {"pos": self.pos, "color": self.color}, indices=self.indices,
        )
        batch.draw(fallback)


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
        # 'TOP_LEFT' | 'RIGHT_CENTER' | 'BOTTOM_LEFT_REGION'
        self.anchor = 'TOP_LEFT'
        self.font_size = 14
        self.padding = 7
        self.gap = 3
        self.corner_radius = 6
        self.background = (0.10, 0.10, 0.10, 0.92)
        self.row_color = (0.22, 0.22, 0.22, 0.9)
        self.hover_color = (0.28, 0.45, 0.75, 0.95)
        self.active_color = (0.20, 0.38, 0.65, 0.95)
        self.alert_color = (0.48, 0.12, 0.12, 0.95)
        self.text_color = (0.92, 0.92, 0.92, 1.0)
        self.separator_color = (1.0, 1.0, 1.0, 0.15)
        self._hover = None
        self._laid_out = False

    # ---- build API (with-statement rebuilds content) ----

    def __enter__(self):
        self.root.children.clear()
        self._stack[:] = [self.root]
        self._laid_out = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._laid_out = False

    def _add(self, node):
        self._stack[-1].children.append(node)
        return node

    def label(self, text="", alert=False):
        return self._add(OverlayNode("LABEL", text=str(text), alert=alert))

    def separator(self):
        return self._add(OverlayNode("SEPARATOR"))

    def operator(self, operator, text=None, active=False):
        props = SimpleNamespace()
        self._add(OverlayNode("OPERATOR", text=text or operator, active=active,
                              operator=operator, properties=props))
        return props

    def prop(self, data, prop, text=None):
        label = text or data.bl_rna.properties[prop].name
        return self._add(OverlayNode("PROPERTY", text=label, data=data, prop=prop))

    def _container(self, kind):
        node = self._add(OverlayNode(kind))
        return _LayoutScope(self, node)

    def row(self):
        return self._container("ROW")

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
        blf.size(0, self.font_size)
        if node.kind in {"LABEL", "OPERATOR", "PROPERTY"}:
            w, h = blf.dimensions(0, self._node_text(node))
            node.size = Vector((w + self.padding * 2, max(h + self.padding * 2, 24)))
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
            if node.kind == "ROW":
                cx += child.size.x + self.gap
            else:
                cy -= child.size.y + self.gap

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
        if self.anchor == 'BOTTOM_LEFT_REGION':
            region = bpy.context.region
            pad = self.padding * 2
            if region is not None:
                return Vector((region.x + pad, region.y + pad + h))
            return Vector((pad, pad + h))
        return Vector((x, y))

    def sync_input(self, offset, mouse):
        """Update anchor/mouse (window px); invalidates hover, not content."""
        offset = Vector(offset)
        mouse = Vector(mouse) if mouse is not None else Vector((-1e6, -1e6))
        if offset != self.offset_position or mouse != self.mouse_position:
            self.offset_position = offset
            self.mouse_position = mouse
            self._laid_out = False

    def _ensure_layout(self):
        if self._laid_out:
            return
        self._measure(self.root)
        origin = self._anchor_origin()
        self._arrange(self.root, origin.x, origin.y)
        self._hover = next(
            (n for n in self._walk()
             if n.kind in {"OPERATOR", "PROPERTY"} and self._contains(n.rect, self.mouse_position)),
            None,
        )
        self._laid_out = True

    @staticmethod
    def _contains(rect, point):
        return bool(rect and rect[0] <= point.x <= rect[2] and rect[1] <= point.y <= rect[3])

    # ---- draw ----

    def _node_fill(self, node):
        if node is self._hover:
            return self.hover_color
        if node.active:
            return self.active_color
        if node.alert and node.kind != "LABEL":
            return self.alert_color
        if node.kind in {"OPERATOR", "PROPERTY"}:
            return self.row_color
        return self.background

    def __gpu_draw__(self):
        if not self.root.children:
            return
        self._ensure_layout()
        region = bpy.context.region
        ox = region.x if region is not None else 0
        oy = region.y if region is not None else 0

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
            if node.kind not in {"OPERATOR", "PROPERTY", "BOX"}:
                continue
            rects.add(x1 - ox, y1 - oy, x2 - ox, y2 - oy,
                      self._node_fill(node), self.corner_radius)

        gpu_draw_begin()
        try:
            rects.draw()
            blf.size(0, self.font_size)
            for node in self._walk():
                if node.kind not in {"LABEL", "OPERATOR", "PROPERTY"} or node.rect is None:
                    continue
                if node.alert and node.kind == "LABEL":
                    blf.color(0, 1.0, 0.45, 0.45, 1.0)
                else:
                    blf.color(0, *self.text_color)
                blf.position(0, node.rect[0] + self.padding - ox,
                             node.rect[1] + self.padding - oy, 0)
                blf.draw(0, self._node_text(node))
        finally:
            gpu_draw_end()

    # ---- events ----

    def check_event(self, event) -> bool:
        """Handle one modal event. True when the overlay consumed it."""
        if not self.root.children:
            return False
        self._ensure_layout()
        node = self._hover
        if node is None:
            return False
        if event.type != 'LEFTMOUSE' or event.value != 'RELEASE':
            return True  # hovered: swallow so clicks cannot fall through
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


class _LayoutScope:
    def __init__(self, layout, node):
        self.layout, self.node = layout, node

    def __enter__(self):
        self.layout._stack.append(self.node)
        return self.layout

    def __exit__(self, exc_type, exc_value, traceback):
        self.layout._stack.pop()
