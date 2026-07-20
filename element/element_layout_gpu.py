"""GPU renderer for row/column/box layout panels (Blender UILayout-like).

A layout container on a direction slot (or hovered inside a menu) opens a
panel next to its button. The panel arranges children with the same semantics
as ``UILayout``: ROW places children side by side, COLUMN stacks them, BOX
stacks them inside chrome. Leaves are operator / property / child-gesture /
divider rows; interactive leaves stamp the same hit-box attributes the
extension machinery already understands (``extension_by_child_draw_area``,
``extension_draw_area`` and the session layout token).
"""

from __future__ import annotations

from types import SimpleNamespace

import bpy
import gpu
from mathutils import Vector

from ..utils.gpu import get_now_2d_offset_position
from ..utils.texture import Texture


class ElementLayoutGpu:
    """Mixin on Element: measure + draw one layout container panel."""

    _LAYOUT_ROW_INTERVAL = 0.4
    _LAYOUT_GAP_FRAC = 0.35
    _LAYOUT_CHEVRON_FRAC = 0.78
    _LAYOUT_SEP_FRAC = 0.4

    def _layout_metrics(self):
        from ..utils.blf_text import text_line_height
        label_h = text_line_height(self.text_size)
        mx, my = self.text_margin
        return SimpleNamespace(
            label_h=label_h,
            row_h=label_h * (1.0 + self._LAYOUT_ROW_INTERVAL),
            gap=label_h * self._LAYOUT_GAP_FRAC,
            pad=float(my),
            margin_x=float(mx),
            margin_y=float(my),
            chevron=label_h * self._LAYOUT_CHEVRON_FRAC,
            sep_h=label_h * self._LAYOUT_SEP_FRAC,
        )

    def _layout_children(self):
        # extension_items is memoized per element per input event on ops.
        return self.extension_items

    def _layout_node_size(self, node, metrics) -> Vector:
        if node.is_layout_container:
            children = node._layout_children()
            sizes = [node._layout_node_size(child, metrics) for child in children]
            if not sizes:
                size = Vector((metrics.row_h * 2.0, metrics.row_h))
            elif node.is_row:
                size = Vector((
                    sum(s.x for s in sizes) + metrics.gap * (len(sizes) - 1),
                    max(s.y for s in sizes),
                ))
            else:
                size = Vector((
                    max(s.x for s in sizes),
                    sum(s.y for s in sizes) + metrics.gap * (len(sizes) - 1),
                ))
            if node.is_box:
                size += Vector((metrics.pad * 2.0, metrics.pad * 2.0))
            return size
        if node.is_dividing_line:
            return Vector((metrics.row_h, metrics.sep_h))
        tw, th = node.text_dimensions
        w = float(tw) + metrics.pad * 2.0
        if node.is_child_gesture or node.is_layout_container:
            w += metrics.gap + metrics.chevron
        if node.is_draw_icon and Texture.get_texture(node._gpu_draw_icon_name()) is not None:
            w += metrics.label_h + metrics.gap
        return Vector((w, metrics.row_h))

    @property
    def layout_panel_content_size(self) -> Vector:
        """Arranged size of this container's children (no outer margin)."""
        metrics = self._layout_metrics()
        children = self._layout_children()
        sizes = [self._layout_node_size(child, metrics) for child in children]
        if not sizes:
            return Vector((metrics.row_h * 3.0, metrics.row_h))
        if self.is_row:
            return Vector((
                sum(s.x for s in sizes) + metrics.gap * (len(sizes) - 1),
                max(s.y for s in sizes),
            ))
        return Vector((
            max(s.x for s in sizes),
            sum(s.y for s in sizes) + metrics.gap * (len(sizes) - 1),
        ))

    @property
    def extension_dimensions(self) -> Vector:
        """Panel content size; containers use layout arrangement."""
        if self.is_layout_container:
            return self.layout_panel_content_size
        from .element_gpu_draw import ElementGpuExtensionItem
        return ElementGpuExtensionItem.extension_dimensions.fget(self)

    def _layout_panel_is_open(self, ops) -> bool:
        session = getattr(ops, 'session', None)
        if session is None:
            return False
        if self in session.extension_hover:
            return True
        snap = session.snapshot
        return snap.direction_element == self and snap.threshold_zone.is_beyond

    def draw_gpu_layout_panel(self, ops):
        """Draw panel chrome + children. Matrix origin = content top-left."""
        self.ops = ops
        metrics = self._layout_metrics()
        content = self.layout_panel_content_size
        w, h = content.x, content.y
        mx, my = metrics.margin_x, metrics.margin_y

        x, y = get_now_2d_offset_position()
        self.extension_draw_area = [x - mx, y - h - my, x + w + mx, y + mx]
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token

        draw = self.draw_property
        stroke, line_width = self._outline_colors(active=False)
        self.draw_rounded_rectangle_outlined(
            (w / 2, -h / 2),
            fill=draw.background_child_color,
            stroke=stroke,
            radius=self.text_radius,
            width=w + mx * 2,
            height=h + my * 2,
            line_width=line_width,
        )

        children = self._layout_children()
        if not children:
            self.draw_text(
                bpy.app.translations.pgettext_iface("No child items. Please add some."),
                size=self.text_size,
                position=[0, 0],
            )
            return
        self._draw_layout_children(children, ops, metrics, w, horizontal=self.is_row)

    def _draw_layout_children(self, children, ops, metrics, avail_w, *, horizontal):
        cursor = 0.0
        for child in children:
            size = self._layout_node_size(child, metrics)
            with gpu.matrix.push_pop():
                if horizontal:
                    gpu.matrix.translate((cursor, 0.0))
                    self._draw_layout_node(child, ops, metrics, size.x)
                else:
                    gpu.matrix.translate((0.0, -cursor))
                    self._draw_layout_node(child, ops, metrics, avail_w)
            cursor += (size.x if horizontal else size.y) + metrics.gap

    def _draw_layout_node(self, node, ops, metrics, avail_w):
        node.ops = ops
        if node.is_layout_container:
            children = node._layout_children()
            size = self._layout_node_size(node, metrics)
            if node.is_box:
                draw = self.draw_property
                stroke, line_width = self._outline_colors(active=False)
                self.draw_rounded_rectangle_outlined(
                    (avail_w / 2, -size.y / 2),
                    fill=draw.background_child_color,
                    stroke=stroke,
                    radius=min(self.text_radius, size.y / 2),
                    width=avail_w,
                    height=size.y,
                    line_width=line_width,
                )
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((metrics.pad, -metrics.pad))
                    self._draw_layout_children(
                        children, ops, metrics, avail_w - metrics.pad * 2.0,
                        horizontal=node.is_row,
                    )
            else:
                self._draw_layout_children(
                    children, ops, metrics, avail_w, horizontal=node.is_row,
                )
            return
        if node.is_dividing_line:
            color = self.draw_property.dividing_line_color
            dh = max(1.0, metrics.sep_h * 0.25)
            with gpu.matrix.push_pop():
                gpu.matrix.translate((avail_w * 0.5, -metrics.sep_h * 0.5))
                self.draw_rounded_rectangle_area(
                    (0, 0), color=color, radius=dh * 0.5, width=avail_w, height=dh,
                )
            return
        self._draw_layout_leaf(node, ops, metrics, avail_w)

    def _draw_layout_leaf(self, item, ops, metrics, avail_w):
        row_h = metrics.row_h
        draw = self.draw_property
        sx, sy = get_now_2d_offset_position()

        item.extension_by_child_draw_area = [sx, sy - row_h, sx + avail_w, sy]
        session = getattr(ops, 'session', None)
        if session is not None:
            item._gesture_layout_token = session.layout_token

        hovered = item.extension_by_child_is_hover
        radius = min(self.text_radius, row_h * 0.5)

        # Slider fill for numeric properties (soft range → row width).
        fraction = item.display_property_fraction if item.is_property_display else None
        if fraction is not None and fraction > 0.0:
            fill_w = max(2.0, avail_w * fraction)
            self.draw_rounded_rectangle_area(
                (fill_w * 0.5, -row_h * 0.5),
                color=draw.background_operator_active_color,
                radius=min(radius, fill_w * 0.5),
                width=fill_w,
                height=row_h,
            )
        if hovered:
            stroke, line_width = self._outline_colors(active=True)
            self.draw_rounded_rectangle_outlined(
                (avail_w * 0.5, -row_h * 0.5),
                fill=item.extension_background_color,
                stroke=stroke,
                radius=radius,
                width=avail_w,
                height=row_h,
                line_width=line_width,
            )

        with gpu.matrix.push_pop():
            gpu.matrix.translate((metrics.pad, -((row_h - metrics.label_h) * 0.5)))
            cursor_x = 0.0
            if item.is_draw_icon:
                texture = Texture.get_texture(item._gpu_draw_icon_name())
                if texture is not None:
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((cursor_x, 0))
                        item.gpu_draw_icon(False, icon_size=metrics.label_h)
                    cursor_x += metrics.label_h + metrics.gap
            with gpu.matrix.push_pop():
                gpu.matrix.translate((cursor_x, 0))
                _tw, th = item.text_dimensions
                if th < metrics.label_h:
                    gpu.matrix.translate((0, -(metrics.label_h - th) * 0.5))
                item.gpu_draw_label(use_offset=False)

        if item.is_child_gesture:
            texture = Texture.get_texture("1")
            if texture is not None:
                s = metrics.chevron
                self.draw_image(
                    [avail_w - s - metrics.pad * 0.5, -(row_h + s) * 0.5],
                    s, s, texture=texture,
                )
            if item.extension_by_child_is_hover or item in getattr(ops, 'extension_hover', []):
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((avail_w + max(metrics.gap, metrics.margin_x), 0))
                    item.draw_gpu_extension_item(ops)
