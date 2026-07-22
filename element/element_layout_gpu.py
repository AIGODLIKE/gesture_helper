"""GPU renderer for row/column/box layout panels (Blender UILayout-like).

Layout containers are presentation nodes: their children are painted directly
in the direction slot, just as ``pie.column()`` / ``pie.row()`` / ``pie.box()``
are drawn inline by Blender. Only child-gesture leaves open a flyout. Every
interactive leaf stamps the same hit boxes used by the extension machinery.
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

    def _empty_layout_size(self, metrics, *, boxed: bool) -> Vector:
        from ..utils.blf_text import measure_text

        text = bpy.app.translations.pgettext_iface("No child items. Please add some.")
        text_w, _text_h = measure_text(text, self.text_size)
        size = Vector((max(metrics.row_h * 3.0, text_w + metrics.pad * 2.0), metrics.row_h))
        if boxed:
            size += Vector((metrics.pad * 2.0, metrics.pad * 2.0))
        return size

    def _layout_node_size(self, node, metrics) -> Vector:
        if node.is_layout_container:
            children = node._layout_children()
            sizes = [node._layout_node_size(child, metrics) for child in children]
            if not sizes:
                return self._empty_layout_size(metrics, boxed=node.is_box)
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
        # Layout containers are inline presentation nodes.  Only a genuine
        # child gesture reserves the flyout chevron column.
        if node.is_child_gesture:
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
            return self._empty_layout_size(metrics, boxed=self.is_box)
        if self.is_row:
            size = Vector((
                sum(s.x for s in sizes) + metrics.gap * (len(sizes) - 1),
                max(s.y for s in sizes),
            ))
        else:
            size = Vector((
                max(s.x for s in sizes),
                sum(s.y for s in sizes) + metrics.gap * (len(sizes) - 1),
            ))
        if self.is_box:
            size += Vector((metrics.pad * 2.0, metrics.pad * 2.0))
        return size

    @property
    def extension_dimensions(self) -> Vector:
        """Panel content size; containers use layout arrangement."""
        if self.is_layout_container:
            return self.layout_panel_content_size
        from .element_gpu_draw import ElementGpuExtensionItem
        return ElementGpuExtensionItem.extension_dimensions.fget(self)

    @property
    def layout_direction_offset(self) -> Vector:
        """Top-left anchor for an inline layout in a radial direction slot."""
        w, h = self.layout_panel_content_size
        mx, my = self.text_margin
        gap = max(float(mx), float(my)) * 1.5
        direction = self.direction
        if direction == '1':
            return Vector((gap, h * 0.5))
        if direction == '2':
            return Vector((gap, h + gap))
        if direction == '3':
            return Vector((-w * 0.5, h + gap))
        if direction == '4':
            return Vector((-w - gap, h + gap))
        if direction == '5':
            return Vector((-w - gap, h * 0.5))
        if direction == '6':
            return Vector((-w - gap, -gap))
        if direction == '7':
            return Vector((-w * 0.5, -gap))
        return Vector((gap, -gap))

    def draw_gpu_layout_panel(self, ops):
        """Draw inline children; only BOX adds container chrome."""
        self.ops = ops
        metrics = self._layout_metrics()
        content = self.layout_panel_content_size
        w, h = content.x, content.y
        mx, my = metrics.margin_x, metrics.margin_y

        x, y = get_now_2d_offset_position()
        self.extension_draw_area = [x - mx, y - h - my, x + w + mx, y + my]
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token

        # Blender UILayout row()/column() are pure flow containers.  Only
        # box() contributes visible chrome; the children supply their own
        # operator/property button surfaces.
        if self.is_box:
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
            self._draw_empty_layout(metrics, w, h, boxed=self.is_box)
            return
        child_w = w
        child_offset = Vector((0.0, 0.0))
        if self.is_box:
            child_w = max(1.0, w - metrics.pad * 2.0)
            child_offset = Vector((metrics.pad, -metrics.pad))
        with gpu.matrix.push_pop():
            gpu.matrix.translate(child_offset)
            self._draw_layout_children(children, ops, metrics, child_w, horizontal=self.is_row)

    def draw_gpu_layout_inline(self, ops, width: float) -> None:
        """Draw a layout inside an existing flyout without outer panel margins."""
        self.ops = ops
        metrics = self._layout_metrics()
        size = self._layout_node_size(self, metrics)
        width = max(float(width), float(size.x))
        x, y = get_now_2d_offset_position()
        self.extension_draw_area = [x, y - size.y, x + width, y]
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token
        self._draw_layout_node(self, ops, metrics, width)

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
                if not children:
                    self._draw_empty_layout(metrics, avail_w, size.y, boxed=True)
                    return
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((metrics.pad, -metrics.pad))
                    self._draw_layout_children(
                        children, ops, metrics, max(1.0, avail_w - metrics.pad * 2.0),
                        horizontal=node.is_row,
                    )
            else:
                if not children:
                    self._draw_empty_layout(metrics, avail_w, size.y, boxed=False)
                    return
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

    def _draw_empty_layout(self, metrics, width, height, *, boxed: bool) -> None:
        if not boxed:
            self.draw_rounded_rectangle_area(
                (width / 2, -height / 2),
                color=self.draw_property.background_child_color,
                radius=min(self.text_radius, height * 0.5),
                width=width,
                height=height,
            )
        offset = metrics.pad
        self.draw_text(
            bpy.app.translations.pgettext_iface("No child items. Please add some."),
            size=self.text_size,
            position=[offset, -offset if boxed else 0.0],
        )

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

        # Stable native-style button surface, with a value slider overlaid for
        # numeric properties.
        if item.is_operator:
            base_color = draw.background_operator_color
        elif item.is_property_display:
            base_color = item._property_background_color(active=False)
        elif item.is_child_gesture:
            base_color = draw.background_child_color
        else:
            base_color = draw.background_child_color
        self.draw_rounded_rectangle_area(
            (avail_w * 0.5, -row_h * 0.5),
            color=base_color,
            radius=radius,
            width=avail_w,
            height=row_h,
        )

        # Slider fill for numeric properties (soft range -> row width).
        fraction = item.display_property_fraction if item.is_property_display else None
        if fraction is not None and fraction > 0.0:
            fill_w = max(2.0, avail_w * fraction)
            self.draw_rounded_rectangle_area(
                (fill_w * 0.5, -row_h * 0.5),
                color=item._property_slider_color(),
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
