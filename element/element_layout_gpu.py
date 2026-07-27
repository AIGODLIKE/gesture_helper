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
    ROUND_CORNERS_ALL,
    aligned_surface_corner_masks,
    blend_layout_hover_color,
    normalize_layout_alignment,
    resolve_box_inset,
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
    _LAYOUT_HOVER_BLEND = 0.35

    @staticmethod
    def _layout_scale_for(node) -> tuple[float, float]:
        """Return bounded X/Y scale, including legacy uniform data."""
        return layout_scale_pair(node)

    @staticmethod
    def _layout_alignment_for(node) -> str:
        return normalize_layout_alignment(getattr(node, 'layout_alignment', 'EXPAND'))

    @staticmethod
    def _layout_align_for(node) -> bool:
        return bool(getattr(node, 'layout_align', True))

    def _layout_hover_color(self, color):
        """Blend a fill toward the active theme color without adding a border."""
        return blend_layout_hover_color(
            color,
            self.draw_property.background_child_active_color,
            self._LAYOUT_HOVER_BLEND,
        )

    def _layout_gap_for(self, node, metrics) -> float:
        # Blender's Layout::row/column sets space_ to zero for align=True.
        return 0.0 if self._layout_align_for(node) else metrics.gap

    def _layout_metrics(self):
        from ..utils.blf_text import text_line_height
        text_size = float(self.text_size)
        label_h = text_line_height(text_size)
        mx, my = self.layout_margin
        return SimpleNamespace(
            text_size=text_size,
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

    def _layout_measure_signature(self, metrics) -> tuple:
        """Inputs that can change static layout dimensions across frames."""
        from ..utils.public_cache import PublicCache

        session = getattr(getattr(self, 'ops', None), 'session', None)
        try:
            locale = bpy.app.translations.locale
        except (AttributeError, RuntimeError):
            locale = None
        return (
            PublicCache.__structure_generation__,
            PublicCache.__derived_generation__,
            getattr(session, '_poll_context_fingerprint', None),
            getattr(session, '_poll_context_revision', 0),
            locale,
            metrics.text_size,
            float(metrics.label_h),
            float(metrics.row_h),
            float(metrics.gap),
            float(metrics.pad_x),
            float(metrics.pad_y),
            float(metrics.chevron),
            float(metrics.sep_h),
        )

    def _prepare_layout_measure_cache(self, metrics) -> None:
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if session is None:
            return
        key = self._layout_measure_signature(metrics)
        if session._layout_measure_cache_key == key:
            return
        session._layout_measure_cache_key = key
        session._layout_measure_cache = {}
        session._layout_measure_stability = {}

    def _layout_node_is_stable(self, node) -> bool:
        """Whether a node's size is independent of live displayed values."""
        session = getattr(getattr(self, 'ops', None), 'session', None)
        stability = getattr(session, '_layout_measure_stability', None)
        cache_key = id(node)
        if stability is not None and cache_key in stability:
            return stability[cache_key]
        if node.is_layout_container:
            stable = all(
                self._layout_node_is_stable(child)
                for child in node._layout_children()
            )
        else:
            stable = not node.is_property_display
        if stability is not None:
            stability[cache_key] = stable
        return stable

    @staticmethod
    def _layout_rect_is_visible(rect) -> bool:
        region = bpy.context.region
        if region is None:
            return True
        x1, y1, x2, y2 = rect
        return (
            x2 > 0.0
            and y2 > 0.0
            and x1 < float(region.width)
            and y1 < float(region.height)
        )

    def _layout_node_size(self, node, metrics) -> Vector:
        session = getattr(getattr(self, 'ops', None), 'session', None)
        frame_cache = getattr(session, '_layout_frame_measure_cache', None)
        stable_cache = getattr(session, '_layout_measure_cache', None)
        cache_key = id(node)
        if frame_cache is not None:
            cached = frame_cache.get(cache_key)
            if cached is not None:
                return cached
        if stable_cache is not None:
            cached = stable_cache.get(cache_key)
            if cached is not None:
                if frame_cache is not None:
                    frame_cache[cache_key] = cached
                return cached

        size = self._measure_layout_node(node, metrics)
        if frame_cache is not None:
            frame_cache[cache_key] = size
        if stable_cache is not None and self._layout_node_is_stable(node):
            stable_cache[cache_key] = size
        return size

    @staticmethod
    def _layout_child_entries(node, metrics):
        """Return children with positive measured area, omitting empty layouts."""
        entries = []
        for child in node._layout_children():
            size = node._layout_node_size(child, metrics)
            if size.x > 0.0 and size.y > 0.0:
                entries.append((child, size))
        return entries

    def _measure_layout_node(self, node, metrics) -> Vector:
        ops = getattr(self, 'ops', None)
        if ops is not None:
            node.ops = ops
        if node.is_layout_container:
            entries = self._layout_child_entries(node, metrics)
            if not entries:
                return Vector((0.0, 0.0))
            sizes = [size for _child, size in entries]
            scale = self._layout_scale_for(node)
            scale_vector = Vector(scale)
            if node.is_row:
                gap = self._layout_gap_for(node, metrics)
                size = Vector((
                    sum(s.x for s in sizes) + gap * (len(sizes) - 1),
                    max(s.y for s in sizes),
                ))
            else:
                gap = self._layout_gap_for(node, metrics)
                size = Vector((
                    max(s.x for s in sizes),
                    sum(s.y for s in sizes) + gap * (len(sizes) - 1),
                ))
            if node.is_box:
                inset_x, inset_y = resolve_box_inset(
                    self._layout_align_for(node),
                    True,
                    metrics.pad_x,
                    metrics.pad_y,
                )
                size += Vector((inset_x * 2.0, inset_y * 2.0))
            size = size * scale_vector
        elif node.is_dividing_line:
            size = Vector((metrics.row_h, metrics.sep_h))
        else:
            tw, _th = node.text_dimensions
            w = float(tw) + metrics.pad_x * 2.0
            status_w, _status_h = node.status_badge_size
            if status_w:
                w += status_w + metrics.gap
            # Layout containers are inline presentation nodes. Only a genuine
            # child gesture reserves the flyout chevron column.
            if node.is_child_gesture:
                w += metrics.gap + metrics.chevron
            if node.is_draw_icon and Texture.get_texture(node._gpu_draw_icon_name()) is not None:
                w += metrics.label_h + metrics.gap
            size = Vector((w, metrics.row_h))
        return size

    @property
    def layout_panel_content_size(self) -> Vector:
        """Arranged size of this container's children (no outer margin)."""
        metrics = self._layout_metrics()
        self._prepare_layout_measure_cache(metrics)
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
        self._prepare_layout_measure_cache(metrics)
        content = self.layout_panel_content_size
        w, h = content.x, content.y
        mx, my = metrics.margin_x, metrics.margin_y

        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token
            self._layout_visible_token = session.layout_token
            self._layout_visible_leaf_items = []
        if w <= 0.0 or h <= 0.0:
            self.extension_draw_area = None
            return
        self.extension_draw_area = get_current_2d_rect(
            (-mx, -h - my, w + mx, my),
        )
        self._draw_layout_node(
            self,
            ops,
            metrics,
            w,
            corner_mask=ROUND_CORNERS_ALL,
        )

    def draw_gpu_layout_inline(self, ops, width: float) -> None:
        """Draw a layout inside an existing flyout without outer panel margins."""
        self.ops = ops
        metrics = self._layout_metrics()
        self._prepare_layout_measure_cache(metrics)
        size = self._layout_node_size(self, metrics)
        session = getattr(ops, 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token
            self._layout_visible_token = session.layout_token
            self._layout_visible_leaf_items = []
        if size.x <= 0.0 or size.y <= 0.0:
            self.extension_draw_area = None
            return
        width = max(float(width), float(size.x))
        self.extension_draw_area = get_current_2d_rect(
            (0.0, -size.y, width, 0.0),
        )
        self._draw_layout_node(
            self,
            ops,
            metrics,
            width,
            corner_mask=ROUND_CORNERS_ALL,
        )

    def _draw_layout_children(
            self, container, children, ops, metrics, avail_w, *, horizontal,
            inside_box=False, outer_corner_mask=ROUND_CORNERS_ALL,
    ):
        """Draw children with Blender-style EXPAND/LEFT/CENTER/RIGHT alignment."""
        sizes = [self._layout_node_size(child, metrics) for child in children]
        alignment = self._layout_alignment_for(container)
        aligned = self._layout_align_for(container)
        gap = 0.0 if aligned else metrics.gap
        corner_masks = (
            aligned_surface_corner_masks(
                (
                    not child.is_dividing_line
                    and (
                        not child.is_layout_container
                        or child.is_box
                        or self._layout_align_for(child)
                    )
                    for child in children
                ),
                horizontal=horizontal,
                outer=outer_corner_mask,
            )
            if aligned
            else (ROUND_CORNERS_ALL,) * len(children)
        )

        if horizontal:
            slots = resolve_layout_line(
                (size.x for size in sizes), avail_w, gap, alignment,
            )
        else:
            slots = None
            cursor = 0.0

        for index, (child, size, corner_mask) in enumerate(
                zip(children, sizes, corner_masks)):
            with gpu.matrix.push_pop():
                if horizontal:
                    x, child_w = slots[index]
                    gpu.matrix.translate((x, 0.0))
                    self._draw_layout_node(
                        child,
                        ops,
                        metrics,
                        child_w,
                        inside_box=inside_box,
                        corner_mask=corner_mask,
                    )
                else:
                    x, child_w = resolve_layout_cross_axis(size.x, avail_w, alignment)
                    gpu.matrix.translate((x, -cursor))
                    self._draw_layout_node(
                        child,
                        ops,
                        metrics,
                        child_w,
                        inside_box=inside_box,
                        corner_mask=corner_mask,
                    )
            if not horizontal:
                cursor += size.y + gap

    def _draw_layout_node(
            self,
            node,
            ops,
            metrics,
            avail_w,
            *,
            inside_box=False,
            corner_mask=ROUND_CORNERS_ALL,
    ):
        node.ops = ops
        if node.is_layout_container:
            entries = self._layout_child_entries(node, metrics)
            if not entries:
                return
            children = [child for child, _size in entries]
            size = self._layout_node_size(node, metrics)
            rect = get_current_2d_rect((0.0, -size.y, avail_w, 0.0))
            if not self._layout_rect_is_visible(rect):
                return
            scale_x, scale_y = self._layout_scale_for(node)
            local_w = max(1.0, float(avail_w) / scale_x)
            local_h = max(1.0, float(size.y) / scale_y)
            with gpu.matrix.push_pop():
                gpu.matrix.scale((scale_x, scale_y, 1.0))
                if node.is_box:
                    draw = self.draw_property
                    stroke, line_width = self._outline_colors(active=False)
                    aligned_box = self._layout_align_for(node) and bool(children)
                    if aligned_box:
                        self.draw_rounded_rectangle_area(
                            (local_w / 2, -local_h / 2),
                            color=draw.background_child_color,
                            radius=self.text_radius,
                            width=local_w,
                            height=local_h,
                            corner_mask=corner_mask,
                        )
                    else:
                        self.draw_rounded_rectangle_outlined(
                            (local_w / 2, -local_h / 2),
                            fill=draw.background_child_color,
                            stroke=stroke,
                            radius=self.text_radius,
                            width=local_w,
                            height=local_h,
                            line_width=line_width,
                            corner_mask=corner_mask,
                        )
                    inset_x, inset_y = resolve_box_inset(
                        aligned_box,
                        True,
                        metrics.pad_x,
                        metrics.pad_y,
                    )
                    child_w = max(1.0, local_w - inset_x * 2.0)
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((inset_x, -inset_y))
                        self._draw_layout_children(
                            node, children, ops, metrics, child_w,
                            horizontal=node.is_row,
                            inside_box=not aligned_box,
                            outer_corner_mask=corner_mask,
                        )
                    if aligned_box:
                        # Child fills share the box boundary; restore the common
                        # border above them so the outer roundbox stays crisp.
                        self.draw_rounded_rectangle_outlined(
                            (local_w / 2, -local_h / 2),
                            fill=(0.0, 0.0, 0.0, 0.0),
                            stroke=stroke,
                            radius=self.text_radius,
                            width=local_w,
                            height=local_h,
                            line_width=line_width,
                            corner_mask=corner_mask,
                        )
                else:
                    self._draw_layout_children(
                        node, children, ops, metrics, local_w,
                        horizontal=node.is_row,
                        inside_box=inside_box,
                        outer_corner_mask=corner_mask,
                    )
            return
        if node.is_dividing_line:
            rect = get_current_2d_rect((0.0, -metrics.sep_h, avail_w, 0.0))
            if not self._layout_rect_is_visible(rect):
                return
            color = self.draw_property.dividing_line_color
            dh = max(1.0, metrics.sep_h * 0.25)
            with gpu.matrix.push_pop():
                gpu.matrix.translate((avail_w * 0.5, -metrics.sep_h * 0.5))
                self.draw_rounded_rectangle_area(
                    (0, 0), color=color, radius=dh * 0.5, width=avail_w, height=dh,
                )
            return
        rect = get_current_2d_rect((0.0, -metrics.row_h, avail_w, 0.0))
        if not self._layout_rect_is_visible(rect):
            return
        visible_items = getattr(self, '_layout_visible_leaf_items', None)
        if visible_items is not None:
            visible_items.append(node)
        self._draw_layout_leaf(
            node,
            ops,
            metrics,
            avail_w,
            inside_box=inside_box,
            draw_rect=rect,
            corner_mask=corner_mask,
        )

    def _draw_layout_leaf(
            self, item, ops, metrics, avail_w, *, inside_box=False,
            draw_rect=None, corner_mask=ROUND_CORNERS_ALL,
    ):
        row_h = metrics.row_h
        draw = self.draw_property
        draw_rect = (
            draw_rect
            if draw_rect is not None
            else get_current_2d_rect((0.0, -row_h, avail_w, 0.0))
        )
        session = getattr(ops, 'session', None)
        draw_ctx = getattr(session, 'draw_ctx', None) if session is not None else None
        mouse = getattr(draw_ctx, 'mouse_region', None) if draw_ctx is not None else None
        from .extension_hit import publish_child_row_hit
        hovered = publish_child_row_hit(item, ops, draw_rect, mouse=mouse)
        # Blender's box() draws one outer roundbox and marks its child buttons
        # as box items, so the content rows do not become separate pills.
        radius = 0.0 if inside_box else self.text_radius

        # Stable native-style button surface, with a value slider overlaid for
        # numeric properties.
        status_info = item.element_status_info
        status_size = item._status_badge_size_for(
            status_info,
            metrics.text_size,
        )
        is_operator = item.is_operator
        is_property_display = item.is_property_display
        is_child_gesture = item.is_child_gesture
        if status_info.status.is_error:
            base_color = item.extension_background_color
        elif is_operator:
            base_color = draw.background_operator_color
        elif is_property_display:
            base_color = item._property_background_color(active=False)
        elif is_child_gesture:
            base_color = draw.background_child_color
        else:
            base_color = draw.background_child_color
        if hovered:
            base_color = self._layout_hover_color(base_color)
        self.draw_rounded_rectangle_area(
            (avail_w * 0.5, -row_h * 0.5),
            color=base_color,
            radius=radius,
            width=avail_w,
            height=row_h,
            corner_mask=corner_mask,
        )

        # Slider fill for numeric properties (soft range -> row width).
        fraction = item.display_property_fraction if is_property_display else None
        if fraction is not None and fraction > 0.0:
            fill_w = max(2.0, avail_w * fraction)
            slider_color = item._property_slider_color()
            if hovered:
                # Apply the same affine blend to both field and slider so the
                # value fraction stays visible while the whole row highlights.
                slider_color = self._layout_hover_color(slider_color)
            self.draw_rounded_rectangle_area(
                (fill_w * 0.5, -row_h * 0.5),
                color=slider_color,
                radius=radius,
                width=fill_w,
                height=row_h,
                corner_mask=corner_mask,
            )
        item.gpu_draw_status_accent(
            (avail_w * 0.5, -row_h * 0.5), avail_w, row_h,
            info=status_info,
        )

        with gpu.matrix.push_pop():
            gpu.matrix.translate((metrics.pad_x, -((row_h - metrics.label_h) * 0.5)))
            cursor_x = 0.0
            status_w, _status_h = status_size
            if status_w:
                with gpu.matrix.push_pop():
                    item.gpu_draw_status_badge(
                        False,
                        slot_width=status_w,
                        info=status_info,
                        badge_size=status_size,
                    )
                cursor_x += status_w + metrics.gap
            icon_name = item._gpu_draw_icon_name()
            if icon_name:
                texture = Texture.get_texture(icon_name)
                if texture is not None:
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((cursor_x, 0))
                        item.gpu_draw_icon(False, icon_size=metrics.label_h)
                    cursor_x += metrics.label_h + metrics.gap
            with gpu.matrix.push_pop():
                gpu.matrix.translate((cursor_x, 0))
                label = (
                    item.display_property_text
                    if is_property_display
                    else item.name_translate
                )
                from .element_gpu_draw import from_text_get_dimensions
                dimensions = from_text_get_dimensions(label, metrics.text_size)
                _tw, th = dimensions
                if th < metrics.label_h:
                    gpu.matrix.translate((0, -(metrics.label_h - th) * 0.5))
                item.gpu_draw_label(
                    use_offset=False,
                    text=label,
                    dimensions=dimensions,
                    color=item._text_color_for(status_info, draw),
                    size=metrics.text_size,
                )

        if is_child_gesture:
            texture = Texture.get_texture("1")
            if texture is not None:
                s = metrics.chevron
                self.draw_image(
                    [avail_w - s - metrics.pad_x * 0.5, -(row_h + s) * 0.5],
                    s, s, texture=texture,
                )
            if hovered or item in getattr(ops, 'extension_hover', []):
                with gpu.matrix.push_pop():
                    gpu.matrix.translate((avail_w + max(metrics.gap, metrics.margin_x), 0))
                    item.draw_gpu_extension_item(ops)
