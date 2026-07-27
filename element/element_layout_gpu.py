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

from ..utils.gpu import get_current_2d_rect
from ..utils.layout_alignment import (
    normalize_layout_alignment,
    resolve_layout_cross_axis,
    resolve_layout_line,
)
from ..utils.layout_scale import layout_scale_pair
from ..utils.texture import Texture


class ElementLayoutGpu:
    """Mixin on Element: measure + draw one layout container panel."""

    _LAYOUT_ROW_INTERVAL = 0.4
    _LAYOUT_GAP_FRAC = 0.35
    _LAYOUT_CHEVRON_FRAC = 0.78
    _LAYOUT_SEP_FRAC = 0.4

    @staticmethod
    def _layout_scale_for(node) -> tuple[float, float]:
        """Return bounded X/Y scale, including legacy uniform data."""
        return layout_scale_pair(node)

    @staticmethod
    def _layout_alignment_for(node) -> str:
        return normalize_layout_alignment(getattr(node, 'layout_alignment', 'EXPAND'))

    def _layout_metrics(self):
        from ..utils.blf_text import text_line_height
        label_h = text_line_height(self.text_size)
        mx, my = self.layout_margin
        return SimpleNamespace(
            label_h=label_h,
            row_h=max(label_h * (1.0 + self._LAYOUT_ROW_INTERVAL), label_h + my * 2.0),
            gap=label_h * self._LAYOUT_GAP_FRAC,
            pad_x=float(mx),
            pad_y=float(my),
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
        size = Vector((max(metrics.row_h * 3.0, text_w + metrics.pad_x * 2.0), metrics.row_h))
        if boxed:
            size += Vector((metrics.pad_x * 2.0, metrics.pad_y * 2.0))
        return size

    def _layout_node_size(self, node, metrics) -> Vector:
        ops = getattr(self, 'ops', None)
        if ops is not None:
            node.ops = ops
        if node.is_layout_container:
            children = node._layout_children()
            sizes = [node._layout_node_size(child, metrics) for child in children]
            scale = self._layout_scale_for(node)
            scale_vector = Vector(scale)
            if not sizes:
                return (
                    self._empty_layout_size(metrics, boxed=node.is_box)
                    * scale_vector
                )
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
                size += Vector((metrics.pad_x * 2.0, metrics.pad_y * 2.0))
            return size * scale_vector
        if node.is_dividing_line:
            return Vector((metrics.row_h, metrics.sep_h))
        tw, th = node.text_dimensions
        w = float(tw) + metrics.pad_x * 2.0
        status_w, _status_h = node.status_badge_size
        if status_w:
            w += status_w + metrics.gap
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
        return self._layout_node_size(self, metrics)

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
        mx, my = self.layout_margin
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
        """Draw this root layout using the same recursive layout path as children."""
        self.ops = ops
        metrics = self._layout_metrics()
        content = self.layout_panel_content_size
        w, h = content.x, content.y
        mx, my = metrics.margin_x, metrics.margin_y

        self.extension_draw_area = get_current_2d_rect(
            (-mx, -h - my, w + mx, my),
        )
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token
        self._draw_layout_node(self, ops, metrics, w)

    def draw_gpu_layout_inline(self, ops, width: float) -> None:
        """Draw a layout inside an existing flyout without outer panel margins."""
        self.ops = ops
        metrics = self._layout_metrics()
        size = self._layout_node_size(self, metrics)
        width = max(float(width), float(size.x))
        self.extension_draw_area = get_current_2d_rect(
            (0.0, -size.y, width, 0.0),
        )
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token
        self._draw_layout_node(self, ops, metrics, width)

    def _draw_layout_children(
            self, container, children, ops, metrics, avail_w, *, horizontal,
            inside_box=False,
    ):
        """Draw children with Blender-style EXPAND/LEFT/CENTER/RIGHT alignment."""
        sizes = [self._layout_node_size(child, metrics) for child in children]
        alignment = self._layout_alignment_for(container)

        if horizontal:
            slots = resolve_layout_line(
                (size.x for size in sizes), avail_w, metrics.gap, alignment,
            )
        else:
            slots = None
            cursor = 0.0

        for index, (child, size) in enumerate(zip(children, sizes)):
            with gpu.matrix.push_pop():
                if horizontal:
                    x, child_w = slots[index]
                    gpu.matrix.translate((x, 0.0))
                    self._draw_layout_node(
                        child, ops, metrics, child_w, inside_box=inside_box,
                    )
                else:
                    x, child_w = resolve_layout_cross_axis(size.x, avail_w, alignment)
                    gpu.matrix.translate((x, -cursor))
                    self._draw_layout_node(
                        child, ops, metrics, child_w, inside_box=inside_box,
                    )
            if not horizontal:
                cursor += size.y + metrics.gap

    def _draw_layout_node(self, node, ops, metrics, avail_w, *, inside_box=False):
        node.ops = ops
        if node.is_layout_container:
            children = node._layout_children()
            size = self._layout_node_size(node, metrics)
            scale_x, scale_y = self._layout_scale_for(node)
            local_w = max(1.0, float(avail_w) / scale_x)
            local_h = max(1.0, float(size.y) / scale_y)
            with gpu.matrix.push_pop():
                gpu.matrix.scale((scale_x, scale_y, 1.0))
                if node.is_box:
                    draw = self.draw_property
                    stroke, line_width = self._outline_colors(active=False)
                    self.draw_rounded_rectangle_outlined(
                        (local_w / 2, -local_h / 2),
                        fill=draw.background_child_color,
                        stroke=stroke,
                        radius=self.text_radius,
                        width=local_w,
                        height=local_h,
                        line_width=line_width,
                    )
                    if not children:
                        self._draw_empty_layout(metrics, local_w, local_h, boxed=True)
                        return
                    child_w = max(1.0, local_w - metrics.pad_x * 2.0)
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((metrics.pad_x, -metrics.pad_y))
                        self._draw_layout_children(
                            node, children, ops, metrics, child_w,
                            horizontal=node.is_row,
                            inside_box=True,
                        )
                else:
                    if not children:
                        self._draw_empty_layout(metrics, local_w, local_h, boxed=False)
                        return
                    self._draw_layout_children(
                        node, children, ops, metrics, local_w,
                        horizontal=node.is_row,
                        inside_box=inside_box,
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
        self._draw_layout_leaf(node, ops, metrics, avail_w, inside_box=inside_box)

    def _draw_empty_layout(self, metrics, width, height, *, boxed: bool) -> None:
        if not boxed:
            self.draw_rounded_rectangle_area(
                (width / 2, -height / 2),
                color=self.draw_property.background_child_color,
                radius=self.text_radius,
                width=width,
                height=height,
            )
        self.draw_text(
            bpy.app.translations.pgettext_iface("No child items. Please add some."),
            size=self.text_size,
            position=[metrics.pad_x, -metrics.pad_y if boxed else 0.0],
        )

    def _draw_layout_leaf(self, item, ops, metrics, avail_w, *, inside_box=False):
        row_h = metrics.row_h
        draw = self.draw_property
        item.extension_by_child_draw_area = get_current_2d_rect(
            (0.0, -row_h, avail_w, 0.0),
        )
        session = getattr(ops, 'session', None)
        if session is not None:
            item._gesture_layout_token = session.layout_token

        hovered = item.extension_by_child_is_hover
        # Blender's box() draws one outer roundbox and marks its child buttons
        # as box items, so the content rows do not become separate pills.
        radius = 0.0 if inside_box else self.text_radius

        # Stable native-style button surface, with a value slider overlaid for
        # numeric properties.
        if item.element_status_info.status.is_error:
            base_color = item.extension_background_color
        elif item.is_operator:
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
                radius=radius,
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
        item.gpu_draw_status_accent(
            (avail_w * 0.5, -row_h * 0.5), avail_w, row_h,
        )

        with gpu.matrix.push_pop():
            gpu.matrix.translate((metrics.pad_x, -((row_h - metrics.label_h) * 0.5)))
            cursor_x = 0.0
            status_w, _status_h = item.status_badge_size
            if status_w:
                with gpu.matrix.push_pop():
                    item.gpu_draw_status_badge(False, slot_width=status_w)
                cursor_x += status_w + metrics.gap
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
                    [avail_w - s - metrics.pad_x * 0.5, -(row_h + s) * 0.5],
                    s, s, texture=texture,
                )
            if item.extension_by_child_is_hover or item in getattr(ops, 'extension_hover', []):
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((avail_w + max(metrics.gap, metrics.margin_x), 0))
                    item.draw_gpu_extension_item(ops)
