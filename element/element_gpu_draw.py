import math
from functools import cache

import bpy
import gpu
from bl_operators.wm import context_path_validate
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector

from ..utils.gpu import get_now_2d_offset_position
from ..utils.gesture_items import get_gesture_extension_items
from ..utils.public import get_pref
from ..utils.public_cache import PublicCache
from ..utils.color import color_to_srgb
from ..utils.public_gpu import PublicGpu
from ..utils.texture import Texture
from .element_status import ElementStatus, get_element_status_info


@cache
def from_text_get_dimensions(text, size):
    """(text width, stable line height) — height never depends on the glyphs."""
    from ..utils.blf_text import measure_text
    return measure_text(text, size)


@cache
def get_position(direction, radius):
    angle = math.radians((int(direction) - 1) * 45)  # Convert degrees to radians
    return Vector((radius * math.cos(angle), radius * math.sin(angle)))


class ElementGpuProperty:

    def _element_ui_scale(self) -> float:
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return ctx.ui_scale
        return bpy.context.preferences.view.ui_scale

    @property
    def element_status_info(self):
        return get_element_status_info(self, ops=getattr(self, "ops", None))

    @property
    def element_status_color(self):
        draw = self.draw_property
        role = self.element_status_info.color_role
        if role == "error":
            return draw.status_error_color
        if role == "warning":
            return draw.status_warning_color
        return draw.status_disabled_color

    @property
    def status_badge_size(self) -> tuple[float, float]:
        info = self.element_status_info
        if info.is_valid:
            return 0.0, 0.0
        size = max(8, round(self.text_size * 0.58))
        width, height = from_text_get_dimensions(info.badge, size)
        pad = max(2.0, height * 0.28)
        return width + pad * 2.0, height + 2.0

    def _draw_frame_ctx(self):
        from ..gesture.draw_frame_context import draw_ctx_from_ops
        return draw_ctx_from_ops(getattr(self, "ops", None))

    @property
    def text_size(self):
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return ctx.text_gpu_draw_size
        scale = bpy.context.preferences.view.ui_scale
        return self.draw_property.text_gpu_draw_size * scale

    @property
    def text_margin(self):
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return [ctx.margin_x, ctx.margin_y]
        scale = bpy.context.preferences.view.ui_scale
        return [i * scale for i in self.draw_property.margin]

    @property
    def text_radius(self):
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return ctx.text_gpu_draw_radius
        scale = bpy.context.preferences.view.ui_scale
        return self.draw_property.text_gpu_draw_radius * scale

    @property
    def text_dimensions(self) -> tuple:
        """(label width, line height) — the height is glyph-independent."""
        return from_text_get_dimensions(self.text, self.text_size)

    @property
    def text(self) -> str:
        if self.is_property_display:
            return self.display_property_text
        return self.name_translate

    @property
    def is_active_direction(self):
        """Selected in the transition band (BEYOND) or confirm zone — not yet fire-ready alone."""
        if self != self.ops.direction_element:
            return False
        session = getattr(self.ops, "session", None)
        snap = getattr(session, "snapshot", None) if session is not None else None
        if snap is not None:
            return snap.threshold_zone.is_beyond
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return self.ops.distance > ctx.threshold
        scale = bpy.context.preferences.view.ui_scale
        return self.ops.distance > self.gesture_property.threshold * scale

    @property
    def is_confirm_direction(self):
        """Past confirm threshold — matches executor / child-enter gate."""
        if self != self.ops.direction_element:
            return False
        session = getattr(self.ops, "session", None)
        snap = getattr(session, "snapshot", None) if session is not None else None
        if snap is not None:
            return snap.threshold_zone.is_confirm
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return self.ops.distance > (ctx.threshold + ctx.threshold_confirm)
        scale = bpy.context.preferences.view.ui_scale
        gp = self.gesture_property
        return self.ops.distance > (gp.threshold + gp.threshold_confirm) * scale

    @property
    def is_draw_context_toggle_operator_bool(self) -> bool:
        is_ops = self.operator_bl_idname == 'wm.context_toggle'
        is_operator_type = self.operator_type == "OPERATOR"
        if not self.is_operator or not is_operator_type:
            # Not operator or script run path
            return False
        elif not is_ops:
            return False
        elif self.get_operator_wm_context_toggle_property_bool is Ellipsis:
            return False
        if 'data_path' not in self.properties:
            return False
        return True

    @property
    def get_operator_wm_context_toggle_property_bool(self) -> [bool]:
        """Return wm.context_toggle operator bool from data_path."""
        if 'data_path' in self.properties:
            return context_path_validate(bpy.context, self.properties['data_path'])
        return False

    @property
    def text_color(self):
        """
        Text color
        :return:
        """
        draw = self.draw_property
        color = tuple(draw.text_active_color if self.is_active_direction else draw.text_default_color)
        status = self.element_status_info.status
        if status is ElementStatus.DISABLED:
            return (*color[:3], color[3] * 0.38)
        if status in {ElementStatus.POLL_BLOCKED, ElementStatus.READ_ONLY_PROPERTY}:
            return (*color[:3], color[3] * 0.72)
        if status.is_error:
            return (*color[:3], color[3] * 0.82)
        return color

    def _in_extension_ui(self) -> bool:
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return ctx.in_extension_ui
        ops = getattr(self, "ops", None)
        if ops is None:
            return False
        return bool(getattr(ops, "mouse_is_in_extension_any_area", False))

    @property
    def background_color(self):
        """
        Background color
        :return:
        """
        draw = self.draw_property
        # Full active fill only in CONFIRM — BEYOND keeps outline via is_active_direction.
        if self.is_confirm_direction and not self._in_extension_ui():
            if self.is_property_display:
                return self._property_background_color(active=True)
            if self.is_operator:
                return draw.background_operator_active_color
            elif self.is_child_gesture or self.is_layout_container:
                return draw.background_child_active_color
        if self.is_operator:
            if self.operator_type == "OPERATOR":
                if self.is_draw_context_toggle_operator_bool:
                    if self.get_operator_wm_context_toggle_property_bool:
                        return draw.background_bool_true
                    else:
                        return draw.background_bool_false
            return draw.background_operator_color
        if self.is_property_display:
            return self._property_background_color(active=False)
        if self.is_child_gesture or self.is_layout_container:
            return draw.background_child_color
        # Unknown element type: fully transparent (never paint a debug/error solid).
        return (0.0, 0.0, 0.0, 0.0)

    def _property_background_color(self, *, active: bool):
        """Idle / active fill for PROPERTY rows by RNA type."""
        draw = self.draw_property
        prop_type = self.display_property_type
        if prop_type == 'BOOLEAN':
            if self.display_property_value:
                return draw.background_bool_true
            return draw.background_bool_false
        if prop_type == 'INT':
            return draw.background_int_active_color if active else draw.background_int_color
        if prop_type == 'FLOAT':
            return draw.background_float_active_color if active else draw.background_float_color
        if active:
            return draw.background_operator_active_color
        return draw.background_operator_color

    def _property_slider_color(self):
        """Slider fill accent for INT / FLOAT soft-range bars."""
        draw = self.draw_property
        prop_type = self.display_property_type
        if prop_type == 'INT':
            return draw.background_int_active_color
        if prop_type == 'FLOAT':
            return draw.background_float_active_color
        return draw.background_operator_active_color

    @property
    def extension_background_color(self):
        draw = self.draw_property
        if self.extension_by_child_is_hover or self in self.ops.extension_hover:
            return draw.background_child_active_color
        return draw.background_child_color


class ElementGpuDraw(PublicGpu, ElementGpuProperty):

    @property
    def radial_outward_vector(self) -> Vector:
        """Unit vector used to push this root overlay away from the center."""
        direction = str(self.direction)
        if direction == '9':
            direction = '7'
        return get_position(direction, 1.0)

    @property
    def radial_draw_offset(self) -> Vector:
        """Automatic frame offset plus the user's persisted manual offset."""
        auto = (0.0, 0.0)
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if session is not None:
            auto = session.radial_auto_offsets.get(self, auto)
        manual = getattr(self, 'overlay_offset', (0.0, 0.0))
        return Vector((
            float(auto[0]) + float(manual[0]),
            float(auto[1]) + float(manual[1]),
        ))

    def radial_base_bounds(self, radius: float) -> tuple[float, float, float, float]:
        """Measure the root overlay exactly as ``draw_gpu_item`` places it.

        Coordinates are relative to the gesture center and intentionally omit
        both automatic and manual offsets.
        """
        direction = str(self.direction)
        margin_x, margin_y = self.text_margin

        if self.is_layout_container:
            width, height = self.layout_panel_content_size
            if direction == '9':
                gap = max(self.text_margin) * 1.5
                y = -self.text_dimensions[1] - gap if (
                    '7' in self.ops.direction_items
                ) else -gap
                origin = get_position('7', radius) + Vector((-width * 0.5, y))
            else:
                origin = get_position(direction, radius) + self.layout_direction_offset
        elif direction == '9':
            if '7' in self.ops.direction_items:
                anchor_offset = self.draw_direction_offset
            else:
                anchor_offset = Vector((0.0, -self.max_height_dimensions))
            width, height = self.extension_dimensions
            origin = (
                get_position('7', radius)
                + anchor_offset
                + Vector((-width * 0.5, 0.0))
            )
        else:
            width, height = self.draw_dimensions
            origin = get_position(direction, radius) + self.draw_direction_offset

        return (
            float(origin.x - margin_x),
            float(origin.y - height - margin_y),
            float(origin.x + width + margin_x),
            float(origin.y + margin_y),
        )

    @property
    def extension_items(self) -> list:
        """Extension items (bottom menu), memoized per element per input event.

        One dict entry per element (bounded); the key part invalidates on every
        modal event and on structure-cache rebuilds, so poll results never
        outlive one event.
        """
        ops = getattr(self, 'ops', None)
        session = getattr(ops, 'session', None)
        cache_key = (
            PublicCache.__derived_generation__,
            getattr(session, 'event_count', 0),
        )
        # One map per (generation, event). Replacing the whole map when the key
        # changes keeps the cache bounded (no per-event residue).
        items_map = None
        if session is not None:
            packed = session._gpu_extension_items_cache
            if packed is None or packed[0] != cache_key:
                items_map = {}
                session._gpu_extension_items_cache = (cache_key, items_map)
            else:
                items_map = packed[1]
            hit = items_map.get(self)
            if hit is not None:
                return hit
        elif ops is not None:
            # Preview / non-session callers: keep a tiny ops-local map.
            packed = getattr(ops, '_gpu_extension_items_cache', None)
            if packed is None or (isinstance(packed, tuple) and packed[0] != cache_key):
                items_map = {}
                ops._gpu_extension_items_cache = (cache_key, items_map)
            elif isinstance(packed, dict):
                items_map = packed
            else:
                items_map = packed[1]
            hit = items_map.get(self)
            if hit is not None:
                return hit
        items = get_gesture_extension_items(self.element)
        if session is not None:
            # Stable proxies: GPU-stamped hit boxes must survive re-walks.
            items = [session.canonical_element(item) for item in items]
        if items_map is not None:
            items_map[self] = items
        return items

    def draw_gpu_item(self, ops):
        """
        Layout metrics

        4 3 2
        5   1
        6 7 8
          9
        """
        self.ops = ops
        radial_offset = self.radial_draw_offset

        direction = self.direction
        # ROW/COLUMN/BOX are inline presentation nodes, not radial buttons.
        # Draw their tree at the direction anchor immediately; only a nested
        # CHILD_GESTURE leaf is allowed to open a flyout.
        if self.is_layout_container:
            ctx = self._draw_frame_ctx()
            radius = ctx.gesture_radius if ctx is not None else (
                get_pref().gesture_property.radius * bpy.context.preferences.view.ui_scale
            )
            if direction == '9':
                position = get_position('7', radius)
                w, _h = self.layout_panel_content_size
                gap = max(self.text_margin) * 1.5
                with gpu.matrix.push_pop():
                    gpu.matrix.translate(position + radial_offset)
                    if '7' in self.ops.direction_items.keys():
                        y = -self.text_dimensions[1] - gap
                    else:
                        y = -gap
                    gpu.matrix.translate((-w * 0.5, y))
                    self.extension_offset_start_position = get_now_2d_offset_position()
                    self.draw_gpu_layout_panel(ops)
            else:
                position = get_position(direction, radius)
                with gpu.matrix.push_pop():
                    gpu.matrix.translate(
                        position + self.layout_direction_offset + radial_offset
                    )
                    self.draw_gpu_layout_panel(ops)
            return

        if direction == '9':
            ctx = self._draw_frame_ctx()
            radius = ctx.gesture_radius if ctx is not None else (
                get_pref().gesture_property.radius * bpy.context.preferences.view.ui_scale
            )
            position = get_position("7", radius)
            with gpu.matrix.push_pop():
                gpu.matrix.translate(position + radial_offset)
                draw_debug_point((1, 1, 0, 1), 2)

                if "7" in self.ops.direction_items.keys():
                    gpu.matrix.translate(self.draw_direction_offset)
                else:
                    gpu.matrix.translate((0, -self.max_height_dimensions))
                w, h = self.extension_dimensions

                draw_debug_point((1, 0, 0, 1))
                self.extension_offset_start_position = get_now_2d_offset_position()
                gpu.matrix.translate((-w / 2, 0))
                self.draw_gpu_extension_item(ops)
            return
        ctx = self._draw_frame_ctx()
        radius = ctx.gesture_radius if ctx is not None else (
            get_pref().gesture_property.radius * bpy.context.preferences.view.ui_scale
        )
        position = get_position(self.direction, radius)

        margin_x, margin_y = self.text_margin

        with gpu.matrix.push_pop():
            gpu.matrix.translate(position + radial_offset)

            w, h = self.draw_dimensions
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.draw_direction_offset)
                self.gpu_draw_margin()
                x, y = get_now_2d_offset_position()
                self.gpu_draw_status_badge()
                self.gpu_draw_icon()
                self.gpu_draw_label()
                self.gpu_draw_child_icon()

                self.item_draw_area = [x - margin_x, y - h - margin_y, x + w + margin_x, y + margin_y]
                self._gesture_layout_token = ops.session.layout_token


    def gpu_draw_label(self, use_offset=True):
        """Draw the label with its line-box top at the current origin.

        ``draw_text`` places the baseline from measured font metrics, so every
        label (CJK, capitals, descenders) fills the same stable line box — no
        per-script nudge tables.
        """
        w, _h = self.text_dimensions
        self.draw_text(
            self.text, position=[0, 0], color=color_to_srgb(self.text_color),
            size=self.text_size,
        )
        if use_offset:
            gpu.matrix.translate((w, 0))

    def _gpu_draw_icon_name(self) -> str | None:
        """Icon name used for GPU draw, or None when icon drawing is disabled."""
        if self.is_property_display:
            state_icon = getattr(self, "property_state_icon", "")
            if callable(state_icon):
                state_icon = state_icon()
            if state_icon:
                return state_icon
        if self.is_draw_context_toggle_operator_bool:
            if not self.draw_property.element_draw_property_toggle_icon:
                return None
            if self.get_operator_wm_context_toggle_property_bool:
                return "CHECKBOX_HLT"
            return "CHECKBOX_DEHLT"
        if self.is_have_icon and self.is_show_icon:
            return self.icon
        return None

    def gpu_draw_icon(self, use_offset=True, icon_size=None):
        icon = self._gpu_draw_icon_name()
        if not icon:
            return
        if icon_size is None:
            icon_size = self.content_icon_size
            if self.is_draw_context_toggle_operator_bool and self.parent_is_extension:
                layout = getattr(self.parent_element, "_extension_layout_cache", None)
                if layout is not None:
                    icon_size = layout.icon_size
        texture = Texture.get_texture(icon)
        if texture is None:
            return
        # Vertically align with text box (origin at top of row content).
        self.draw_image([0, -icon_size], icon_size, icon_size, texture=texture)
        if use_offset:
            gpu.matrix.translate((icon_size + self.content_gap, 0))

    def gpu_draw_child_icon(self, use_offset=True):
        if not self.is_draw_child_icon:
            return
        texture = Texture.get_texture("1")
        if texture is None:
            return
        size = self.content_chevron_size
        row_h = self.content_icon_size
        y = -(row_h + size) * 0.5
        gpu.matrix.translate((self.content_gap, 0))
        self.draw_image([0, y], size, size, texture=texture)
        if use_offset:
            gpu.matrix.translate((size, 0))

    def gpu_draw_status_badge(self, use_offset=True, slot_width=None):
        """Draw a compact status code; color carries severity, text carries cause."""
        info = self.element_status_info
        width, height = self.status_badge_size
        if info.is_valid or width <= 0.0:
            return
        slot_width = max(width, float(slot_width or width))
        y = -(self.content_icon_size + height) * 0.5
        self.draw_rounded_rectangle_area(
            (width * 0.5, y + height * 0.5),
            color=self.element_status_color,
            radius=min(3.0 * self._element_ui_scale(), height * 0.25),
            width=width,
            height=height,
        )
        badge_size = max(8, round(self.text_size * 0.58))
        text_w, text_h = from_text_get_dimensions(info.badge, badge_size)
        self.draw_text(
            info.badge,
            position=((width - text_w) * 0.5, y + (height + text_h) * 0.5),
            size=badge_size,
            color=(1.0, 1.0, 1.0, 0.96),
        )
        if use_offset:
            gpu.matrix.translate((slot_width + self.content_gap, 0))

    def gpu_draw_status_accent(self, center, width, height):
        info = self.element_status_info
        if info.is_valid:
            return
        scale = self._element_ui_scale()
        bar_w = max(2.0, 2.0 * scale)
        inset = max(2.0, 2.0 * scale)
        x = center[0] - width * 0.5 + inset + bar_w * 0.5
        self.draw_rounded_rectangle_area(
            (x, center[1]),
            color=self.element_status_color,
            radius=bar_w * 0.5,
            width=bar_w,
            height=max(2.0, height - inset * 2.0),
        )

    def _outline_colors(self, *, active: bool = False):
        draw = self.draw_property
        ctx = self._draw_frame_ctx()
        scale = ctx.ui_scale if ctx is not None else bpy.context.preferences.view.ui_scale
        stroke = draw.outline_active_color if active else draw.outline_color
        # Keep sub-pixel widths so POLYLINE AA stays thin and faint.
        return stroke, max(0.5, float(draw.outline_width) * scale)

    def gpu_draw_margin(self):
        w, h = self.draw_dimensions
        wm, hm = self.text_margin
        with gpu.matrix.push_pop():
            gpu.matrix.translate((w / 2, -h / 2))
            draw_debug_point()

            radius = self.text_radius if (h / 2 > self.text_radius) else h / 2
            # BEYOND: active outline only; CONFIRM: outline + filled background.
            stroke, line_width = self._outline_colors(
                active=self.is_active_direction and not self._in_extension_ui(),
            )
            if self.is_active_direction and not self.is_confirm_direction:
                # Softer outline in the transition band.
                stroke = (*stroke[:3], stroke[3] * 0.65 if len(stroke) > 3 else 0.65)
            self.draw_rounded_rectangle_outlined(
                (0, 0),
                fill=self.background_color,
                stroke=stroke,
                radius=radius,
                width=w + wm * 2,
                height=h + hm * 2,
                line_width=line_width,
            )
            self.gpu_draw_status_accent(
                (0.0, 0.0), w + wm * 2.0, h + hm * 2.0,
            )

    # Gap between icon / label / chevron as a fraction of icon size (menu-style).
    _CONTENT_GAP_FRAC = 0.35
    _CHEVRON_FRAC = 0.78

    @property
    def content_icon_size(self) -> float:
        """Square icon slot matching text height."""
        return float(self.text_dimensions[1])

    @property
    def content_gap(self) -> float:
        return self.content_icon_size * self._CONTENT_GAP_FRAC

    @property
    def content_chevron_size(self) -> float:
        return self.content_icon_size * self._CHEVRON_FRAC

    @property
    def icon_offset_width(self) -> float:
        """Advance after a left icon: icon box + gap."""
        return self.content_icon_size + self.content_gap

    @property
    def draw_dimensions(self) -> Vector:
        """Radial button content size: [icon?][gap][label][gap][chevron?]."""
        tw, th = self.text_dimensions
        w = float(tw)
        gap = self.content_gap
        status_w, _status_h = self.status_badge_size
        if status_w:
            w += status_w + gap
        if self.is_draw_icon and Texture.get_texture(self._gpu_draw_icon_name()) is not None:
            w += self.content_icon_size + gap
        if self.is_draw_child_icon and Texture.get_texture("1") is not None:
            w += gap + self.content_chevron_size
        return Vector((w, th))

    @property
    def draw_direction_offset(self) -> Vector:
        w, h = self.draw_dimensions
        hb = h / 2  # bisect
        wb = w / 2
        offset = [0, 0]
        direction = self.direction
        if direction == '1':
            offset = (0, hb)
        elif direction == '2':
            offset = (0, h)
        elif direction == '3':
            offset = (-wb, h * 2)
        elif direction == '4':
            offset = (-w, h)
        elif direction == '5':
            offset = (-w, hb)
        elif direction == '6':
            offset = (-w, 0)
        elif direction == '7':
            offset = (-wb, -h)
        elif direction == '8':
            offset = (0, 0)
        elif direction == '9':
            offset = (0, -h * get_pref().draw_property.element_extension_item_offset)
        return Vector(offset)


class ElementGpuExtensionItem:
    """Bottom / nested flyout (direction 9) layout.

    Measure content only; outer margin (scaled via text_margin) is chrome around
    the panel — same split as radial buttons. Do not bake margin into content size.

    Row columns: ``[icon?][gap][label........][gap][chevron?]``
    - Left icon column only if any row draws a left icon (aligned slots).
    - Right chevron column only if any row is a child gesture (right-aligned).
    """

    # Horizontal gap between icon / label / chevron (fraction of icon size).
    _GAP_FRAC = 0.35
    _CHEVRON_FRAC = 0.78
    # Extra vertical space inside each row; total row height = icon * (1 + interval).
    _ROW_INTERVAL = 0.4
    # Padding above and below a dividing line (fraction of icon size each side).
    _SEP_PAD_FRAC = 0.2

    @property
    def dividing_line_height(self) -> float:
        dividing_line_height = self.draw_property.dividing_line_height
        ctx = self._draw_frame_ctx()
        scale = ctx.ui_scale if ctx is not None else bpy.context.preferences.view.ui_scale
        return dividing_line_height * scale

    def _separator_metrics(self, icon_size: float) -> tuple[float, float]:
        """Return (line thickness, total separator step) with equal pad above/below."""
        dh = self.dividing_line_height
        pad = float(icon_size) * self._SEP_PAD_FRAC
        return dh, dh + pad * 2.0

    @property
    def max_height_dimensions(self) -> float:
        """Tallest label among extension rows (used by direction-9 offset)."""
        return max((0.0, *(item.text_dimensions[1] for item in self.extension_items if not item.is_dividing_line)))

    @property
    def max_width_dimensions(self) -> float:
        return max((0.0, *(item.text_dimensions[0] for item in self.extension_items if not item.is_dividing_line)))

    @property
    def max_dimensions(self) -> Vector:
        return Vector((self.max_width_dimensions, self.max_height_dimensions))

    def _compute_extension_layout(self):
        """Measure flyout content box (no outer margin)."""
        from types import SimpleNamespace

        items = self.extension_items
        regular_items = [item for item in items if not item.is_layout_container]
        label_w = max((0.0, *(item.text_dimensions[0] for item in regular_items if not item.is_dividing_line)))
        # Stable metric line height — identical for every label at this size.
        from ..utils.blf_text import text_line_height
        label_h = text_line_height(self.text_size)

        icon_size = label_h
        gap = icon_size * self._GAP_FRAC
        chevron_size = icon_size * self._CHEVRON_FRAC
        row_h = icon_size * (1.0 + self._ROW_INTERVAL)

        has_icon_col = False
        has_chevron_col = False
        status_col_w = 0.0
        for item in items:
            if item.is_dividing_line:
                continue
            item.ops = self.ops
            status_col_w = max(status_col_w, item.status_badge_size[0])
            if item.is_draw_icon and Texture.get_texture(item._gpu_draw_icon_name()) is not None:
                has_icon_col = True
            if item.is_child_gesture and Texture.get_texture("1") is not None:
                has_chevron_col = True

        # Content width = columns only (old code always added icon*2 even when unused).
        content_w = label_w
        if status_col_w:
            content_w += status_col_w + gap
        if has_icon_col:
            content_w += icon_size + gap
        if has_chevron_col:
            content_w += gap + chevron_size

        content_h = 0.0
        layout_metrics = self._layout_metrics()
        layout_sizes = {}
        for item in items:
            if item.is_dividing_line:
                _dh, sep_step = self._separator_metrics(icon_size)
                content_h += sep_step
            elif item.is_layout_container:
                size = item._layout_node_size(item, layout_metrics)
                layout_sizes[id(item)] = size
                content_w = max(content_w, float(size.x))
                content_h += float(size.y)
            else:
                content_h += row_h

        mx, my = self.text_margin  # scaled; outer chrome only

        layout = SimpleNamespace(
            margin_x=float(mx),
            margin_y=float(my),
            gap=gap,
            icon_size=icon_size,
            chevron_size=chevron_size,
            row_h=row_h,
            label_w=label_w,
            label_h=label_h,
            has_icon_col=has_icon_col,
            has_chevron_col=has_chevron_col,
            status_col_w=status_col_w,
            content_w=content_w,
            content_h=content_h,
            layout_sizes=layout_sizes,
        )
        self._extension_layout_cache = layout
        # Compat aliases (toggle-icon path / debug).
        self.extension_icon_size = icon_size
        self.extension_icon_interval = gap
        self.extension_text_width = label_w
        return layout

    @property
    def extension_dimensions(self) -> Vector:
        lay = self._compute_extension_layout()
        return Vector((lay.content_w, lay.content_h))

    def draw_gpu_extension_item(self, ops):
        lay = self._compute_extension_layout()
        w = lay.content_w
        with gpu.matrix.push_pop():
            self.ops = ops
            draw_debug_point()
            self.draw_gpu_extension_margin()

            # Origin = top-left of content box; outer margin is only on background/hit box.
            for item in self.extension_items:
                item.ops = ops

                if item.is_layout_container:
                    size = lay.layout_sizes.get(id(item))
                    if size is None:
                        size = item._layout_node_size(item, item._layout_metrics())
                    with gpu.matrix.push_pop():
                        item.draw_gpu_layout_inline(ops, w)
                    gpu.matrix.translate((0, -float(size.y)))
                    draw_debug_point()
                    continue

                if item.is_dividing_line:
                    color = self.draw_property.dividing_line_color
                    dh, step = self._separator_metrics(lay.icon_size)
                    pad = (step - dh) * 0.5
                    with gpu.matrix.push_pop():
                        # Center the line in the separator slot (equal gap above/below).
                        gpu.matrix.translate((w * 0.5, -(pad + dh * 0.5)))
                        self.draw_rounded_rectangle_area(
                            (0, 0),
                            color=color,
                            radius=max(1.0, dh * 0.5),
                            width=w,
                            height=dh,
                        )
                    gpu.matrix.translate((0, -step))
                    continue

                row_h = lay.row_h
                mx, my = lay.margin_x, lay.margin_y
                # Panel chrome is content + (mx, my). Top gap above the first row
                # is ``my``; keep the same inset on left/right so hover padding
                # matches on X and Y.
                hover_w = max(1.0, w + mx * 2.0 - my * 2.0)
                side_inset = my
                # Numeric property rows paint a slider fill over the soft range.
                fraction = item.display_property_fraction if item.is_property_display else None
                if fraction is not None and fraction > 0.0:
                    fill_w = max(2.0, hover_w * fraction)
                    left = w * 0.5 - hover_w * 0.5
                    self.draw_rounded_rectangle_area(
                        (left + fill_w * 0.5, -row_h * 0.5),
                        color=item._property_slider_color(),
                        radius=min(self.text_radius, row_h * 0.5, fill_w * 0.5),
                        width=fill_w,
                        height=row_h,
                    )
                if item.extension_by_child_is_hover:
                    stroke, line_width = self._outline_colors(active=True)
                    self.draw_rounded_rectangle_outlined(
                        (w * 0.5, -row_h * 0.5),
                        fill=item.extension_background_color,
                        stroke=stroke,
                        radius=min(self.text_radius, row_h * 0.5),
                        width=hover_w,
                        height=row_h,
                        line_width=line_width,
                    )
                item.gpu_draw_status_accent(
                    (w * 0.5, -row_h * 0.5), hover_w, row_h,
                )

                sx, sy = get_now_2d_offset_position()
                with gpu.matrix.push_pop():
                    # Vertically center the icon/text band inside the row.
                    gpu.matrix.translate((0, -((row_h - lay.icon_size) * 0.5)))

                    cursor_x = 0.0
                    if lay.status_col_w:
                        with gpu.matrix.push_pop():
                            gpu.matrix.translate((cursor_x, 0))
                            item.gpu_draw_status_badge(False, slot_width=lay.status_col_w)
                        cursor_x += lay.status_col_w + lay.gap
                    if lay.has_icon_col:
                        if item.is_draw_icon:
                            if item.is_draw_context_toggle_operator_bool:
                                if item.get_operator_wm_context_toggle_property_bool:
                                    stroke, line_width = self._outline_colors(active=True)
                                    s = lay.icon_size
                                    self.draw_rounded_rectangle_outlined(
                                        (s * 0.5, -s * 0.5),
                                        fill=self.draw_property.background_child_active_color,
                                        stroke=stroke,
                                        radius=s * 0.5,
                                        width=s,
                                        height=s,
                                        line_width=line_width,
                                    )
                            with gpu.matrix.push_pop():
                                gpu.matrix.translate((cursor_x, 0))
                                # Same slot size for every row so icons share one column.
                                item.gpu_draw_icon(False, icon_size=lay.icon_size)
                        cursor_x += lay.icon_size + lay.gap

                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((cursor_x, 0))
                        # Line box == icon band when heights match; the guard
                        # centers the box if the band is ever taller.
                        _tw, th = item.text_dimensions
                        if th < lay.icon_size:
                            gpu.matrix.translate((0, -(lay.icon_size - th) * 0.5))
                        item.gpu_draw_label(use_offset=False)

                    # Row/column/box content is already rendered inline; the
                    # chevron is reserved for actual child-gesture flyouts.
                    if lay.has_chevron_col and item.is_child_gesture:
                        tex = Texture.get_texture("1")
                        if tex is not None:
                            s = lay.chevron_size
                            chev_x = w - s
                            y = -(lay.icon_size + s) * 0.5
                            self.draw_image([chev_x, y], s, s, texture=tex)

                # Hit box matches the inset hover rect.
                item.extension_by_child_draw_area = [
                    sx - mx + side_inset,
                    sy - row_h,
                    sx + w + mx - side_inset,
                    sy,
                ]
                item._gesture_layout_token = ops.session.layout_token

                if item.is_child_gesture and (
                        item.extension_by_child_is_hover or item in ops.extension_hover
                ):
                    with gpu.matrix.push_pop():
                        gpu.matrix.translate((w + max(lay.gap, lay.margin_x), 0))
                        item.draw_gpu_extension_item(ops)

                gpu.matrix.translate((0, -row_h))
                draw_debug_point()

            if len(self.extension_items) == 0:
                self.draw_text(
                    bpy.app.translations.pgettext_iface("No child items. Please add some."),
                    size=self.text_size,
                    position=[0, 0])

    def draw_gpu_extension_margin(self):
        draw = self.draw_property
        lay = getattr(self, "_extension_layout_cache", None) or self._compute_extension_layout()
        w, h = lay.content_w, lay.content_h
        mx, my = lay.margin_x, lay.margin_y
        x, y = get_now_2d_offset_position()
        self.extension_draw_area = [x - mx, y - h - my, x + w + mx, y + my]
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token

        if len(self.extension_items) == 0:
            return
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


def draw_debug_point(color=(0, 1, 1, 1), radius=1):
    if get_pref().debug_property.debug_extension:
        draw_circle_2d([0, 0], color, radius)
