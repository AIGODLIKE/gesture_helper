import math
from functools import cache

import bpy
import gpu
from bl_operators.wm import context_path_validate
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector

from ..utils.gpu import get_current_2d_rect, get_now_2d_offset_position
from ..utils.gesture_items import get_gesture_extension_items
from ..utils.public import get_pref
from ..utils.public_cache import PublicCache
from ..utils.color import color_to_srgb
from ..utils.layout_alignment import (
    blend_layout_hover_color,
    resolve_extension_row_bounds,
    separator_line_width,
)
from ..utils.ui_theme import interaction_color
from ..utils.public_gpu import PublicGpu
from ..utils.number_arrows import (
    NUMBER_HOVER_BLEND,
    NUMBER_PART_DECREMENT,
    NUMBER_PART_INCREMENT,
    NUMBER_PART_VALUE,
    NUMBER_PRESSED_BLEND,
    number_arrow_chevron,
    number_edge_color,
    number_field_corner_masks,
    number_field_part,
    number_field_rects,
    number_arrow_slot_width,
    show_number_arrows,
)
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
    def runtime_annotation_text(self) -> str:
        """Native source annotation, or the current status reason when blocked."""
        info = self.element_status_info
        if not info.is_valid:
            return info.message
        return self.source_description

    @property
    def status_badge_size(self) -> tuple[float, float]:
        info = self.element_status_info
        return self._status_badge_size_for(info, self.text_size)

    @staticmethod
    def _status_badge_size_for(info, text_size) -> tuple[float, float]:
        if info.is_valid:
            return 0.0, 0.0
        size = max(8, round(text_size * 0.58))
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
    def layout_margin(self):
        ctx = self._draw_frame_ctx()
        if ctx is not None:
            return [ctx.layout_margin_x, ctx.layout_margin_y]
        scale = bpy.context.preferences.view.ui_scale
        return [i * scale for i in self.draw_property.layout_margin]

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
        return self._text_color_for(
            self.element_status_info,
            self.draw_property,
        )

    def _text_color_for(self, info, draw):
        """
        Text color
        :return:
        """
        status = info.status
        if status.is_error:
            color = tuple(draw.text_active_color)
            return (*color[:3], max(0.92, color[3]))
        active = self.is_active_direction
        if self.numeric_arrows_visible:
            hovered_part, pressed_part = self._numeric_field_states()
            active = bool(
                active
                or hovered_part == NUMBER_PART_VALUE
                or pressed_part == NUMBER_PART_VALUE
            )
        color = tuple(draw.text_active_color if active else draw.text_default_color)
        if status is ElementStatus.DISABLED:
            return tuple(getattr(
                draw,
                'text_disabled_color',
                (*color[:3], color[3] * 0.38),
            ))
        if status in {ElementStatus.POLL_BLOCKED, ElementStatus.READ_ONLY_PROPERTY}:
            disabled = tuple(getattr(
                draw,
                'text_disabled_color',
                (*color[:3], color[3] * 0.72),
            ))
            return (*disabled[:3], max(0.72, disabled[3]))
        return color

    @property
    def ui_is_pressed(self) -> bool:
        session = getattr(getattr(self, 'ops', None), 'session', None)
        pressed = getattr(session, '_ui_pressed_element', None) if session is not None else None
        if pressed is self:
            return True
        try:
            return bool(pressed is not None and pressed == self)
        except (ReferenceError, RuntimeError, TypeError):
            return False

    def ui_surface_color(self, base, *, hovered=False, pressed=None):
        if pressed is None:
            pressed = self.ui_is_pressed
        return interaction_color(
            self.draw_property,
            base,
            hovered=bool(hovered),
            pressed=bool(pressed),
        )

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
        if self.element_status_info.status.is_error:
            return draw.status_error_color
        # Direction selection maps onto the same interaction vocabulary used
        # by menus: BEYOND is hover-like, CONFIRM is press-like.
        if self.is_operator:
            if self.operator_type == "OPERATOR":
                if self.is_draw_context_toggle_operator_bool:
                    if self.get_operator_wm_context_toggle_property_bool:
                        base = draw.background_bool_true
                    else:
                        base = draw.background_bool_false
                else:
                    base = draw.background_operator_color
            else:
                base = draw.background_operator_color
            active = draw.background_operator_active_color
        elif self.is_property_display:
            base = self._property_background_color(active=False)
            active = self._property_background_color(active=True)
        elif self.is_child_gesture or self.is_layout_container:
            base = draw.background_child_color
            active = draw.background_child_active_color
        else:
            return (0.0, 0.0, 0.0, 0.0)

        if self._in_extension_ui():
            return base
        if self.ui_is_pressed:
            return self.ui_surface_color(base, pressed=True)
        if self.is_confirm_direction:
            return self.ui_surface_color(active, pressed=True)
        if self.is_active_direction:
            return self.ui_surface_color(base, hovered=True, pressed=False)
        return base

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
    def numeric_arrows_visible(self) -> bool:
        return bool(
            self.is_property_display
            and self.display_property_type in {'INT', 'FLOAT'}
            and self.display_property_is_editable
            and show_number_arrows()
        )

    def numeric_arrow_slot(self, row_height: float) -> float:
        if not self.numeric_arrows_visible:
            return 0.0
        return number_arrow_slot_width(row_height)

    def publish_numeric_arrow_areas(self, rect, row_height: float) -> float:
        slot = self.numeric_arrow_slot(row_height)
        decrement, value, increment = number_field_rects(rect, slot)
        self.property_decrement_draw_area = decrement
        self.property_value_draw_area = value
        self.property_increment_draw_area = increment
        return slot

    def _numeric_field_states(self):
        ctx = self._draw_frame_ctx()
        mouse = getattr(ctx, 'mouse_region', None) if ctx is not None else None
        hovered = number_field_part(
            mouse,
            getattr(self, 'property_decrement_draw_area', None),
            getattr(self, 'property_value_draw_area', None),
            getattr(self, 'property_increment_draw_area', None),
        )
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if (
                session is not None
                and getattr(session, '_numeric_pressed_element', None) == self
        ):
            pressed = getattr(session, '_numeric_pressed_part', None)
        else:
            pressed = None
        return hovered, pressed

    def gpu_draw_numeric_arrows(
            self,
            width: float,
            row_height: float,
            *,
            field_left: float = 0.0,
            field_right: float | None = None,
            field_top: float = 0.0,
            field_bottom: float | None = None,
            slot_width: float | None = None,
            draw_value: bool = True,
            field_corner_mask=None,
    ) -> float:
        """Draw a native three-part number field in local screen space."""
        slot = (
            self.numeric_arrow_slot(row_height)
            if slot_width is None
            else max(0.0, float(slot_width))
        )
        if slot <= 0.0:
            return 0.0
        field_left = float(field_left)
        field_right = float(width if field_right is None else field_right)
        field_top = float(field_top)
        field_bottom = float(
            -row_height if field_bottom is None else field_bottom
        )
        field_height = max(0.0, field_top - field_bottom)
        if field_right <= field_left:
            return 0.0
        slot = min(slot, (field_right - field_left) * 0.5)
        if field_height <= 0.0:
            return 0.0
        hovered, pressed = self._numeric_field_states()
        base = self._property_background_color(active=False)
        active = self._property_background_color(active=True)
        center_y = (field_top + field_bottom) * 0.5
        decrement_mask, value_mask, increment_mask = number_field_corner_masks(
            field_corner_mask,
        )
        part_rects = (
            (
                NUMBER_PART_DECREMENT,
                field_left,
                field_left + slot,
                decrement_mask,
            ),
            (
                NUMBER_PART_VALUE,
                field_left + slot,
                field_right - slot,
                value_mask,
            ),
            (
                NUMBER_PART_INCREMENT,
                field_right - slot,
                field_right,
                increment_mask,
            ),
        )
        for part, left, right, corner_mask in part_rects:
            if right <= left:
                continue
            if part == pressed:
                color = blend_layout_hover_color(
                    base, active, NUMBER_PRESSED_BLEND,
                )
            elif part == hovered:
                color = blend_layout_hover_color(
                    base, active, NUMBER_HOVER_BLEND,
                )
            elif part == NUMBER_PART_VALUE and not draw_value:
                # Layout/menu rows paint the value surface and slider before
                # the edge controls; keep that value fill visible at rest.
                continue
            elif part == NUMBER_PART_VALUE:
                color = base
            else:
                color = number_edge_color(base)
            self.draw_rounded_rectangle_area(
                ((left + right) * 0.5, center_y),
                color=color,
                radius=min(self.text_radius, field_height * 0.32),
                width=right - left,
                height=field_height,
                corner_mask=corner_mask,
            )

        half_w, half_h, line_width = number_arrow_chevron(field_height, slot)
        for part, center_x, direction in (
            (
                NUMBER_PART_DECREMENT,
                field_left + slot * 0.5,
                -1,
            ),
            (
                NUMBER_PART_INCREMENT,
                field_right - slot * 0.5,
                1,
            ),
        ):
            tip_x = center_x + direction * half_w
            back_x = center_x - direction * half_w
            color = (
                self.draw_property.text_active_color
                if part in {hovered, pressed}
                else self.text_color
            )
            self.draw_2d_line(
                ((back_x, center_y + half_h), (tip_x, center_y)),
                color=color,
                line_width=line_width,
            )
            self.draw_2d_line(
                ((tip_x, center_y), (back_x, center_y - half_h)),
                color=color,
                line_width=line_width,
            )
        return slot

    @property
    def extension_background_color(self):
        draw = self.draw_property
        if self.element_status_info.status.is_error:
            return draw.status_error_color
        if self.is_operator:
            base = draw.background_operator_color
        elif self.is_property_display:
            base = self._property_background_color(active=False)
        else:
            base = draw.background_child_color
        hovered = bool(
            self.extension_by_child_is_hover
            or self in getattr(self.ops, 'extension_hover', ())
        )
        return self.ui_surface_color(base, hovered=hovered)


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
        margin_x, margin_y = (
            self.layout_margin
            if self.is_layout_container or direction == '9'
            else self.text_margin
        )

        if self.is_layout_container:
            width, height = self.layout_panel_content_size
            if direction == '9':
                gap = max(self.layout_margin) * 1.5
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
        """Extension items (bottom menu), memoized per content/context state.

        Poll expressions depend on Blender context rather than cursor position,
        so ordinary mouse motion must not rebuild the condition tree. One dict
        entry per element is retained while the derived generation and poll
        fingerprint stay unchanged.
        """
        ops = getattr(self, 'ops', None)
        session = getattr(ops, 'session', None)
        poll_key = getattr(session, '_poll_context_fingerprint', None)
        if poll_key is None:
            try:
                from ..utils.gesture_items import poll_context_fingerprint
                poll_key = poll_context_fingerprint()
                if session is not None:
                    session._poll_context_fingerprint = poll_key
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                poll_key = ()
        poll_key = (
            poll_key,
            getattr(session, '_poll_context_revision', 0),
        )
        cache_key = (
            PublicCache.__derived_generation__,
            poll_key,
        )
        # One map per (generation, context). Replacing the whole map when the
        # key changes keeps the cache bounded (no per-event residue).
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
        # Layout containers are inline presentation nodes, not radial buttons.
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
                gap = max(self.layout_margin) * 1.5
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
                numeric_field = self.numeric_arrows_visible
                field_left = -margin_x if numeric_field else 0.0
                field_right = w + margin_x if numeric_field else w
                field_top = margin_y if numeric_field else 0.0
                field_bottom = -h - margin_y if numeric_field else -h
                field_rect = get_current_2d_rect(
                    (field_left, field_bottom, field_right, field_top),
                )
                self.item_draw_area = (
                    field_rect
                    if numeric_field
                    else get_current_2d_rect(
                        (-margin_x, -h - margin_y, w + margin_x, margin_y),
                    )
                )
                if numeric_field:
                    arrow_slot = self.publish_numeric_arrow_areas(field_rect, h)
                    self.gpu_draw_numeric_arrows(
                        w,
                        h,
                        field_left=field_left,
                        field_right=field_right,
                        field_top=field_top,
                        field_bottom=field_bottom,
                        slot_width=arrow_slot,
                    )
                    self.gpu_draw_status_accent(
                        ((field_left + field_right) * 0.5,
                         (field_top + field_bottom) * 0.5),
                        field_right - field_left,
                        field_top - field_bottom,
                    )
                    self.gpu_draw_numeric_field_frame(
                        field_left=field_left,
                        field_right=field_right,
                        field_top=field_top,
                        field_bottom=field_bottom,
                    )
                else:
                    self.gpu_draw_margin()
                    arrow_slot = 0.0
                    self.property_decrement_draw_area = None
                    self.property_value_draw_area = None
                    self.property_increment_draw_area = None
                if arrow_slot:
                    gpu.matrix.translate((field_left + arrow_slot, 0.0))
                self.gpu_draw_status_badge()
                self.gpu_draw_icon()
                self.gpu_draw_label()
                self.gpu_draw_child_icon()

                self._gesture_layout_token = ops.session.layout_token


    def gpu_draw_label(
            self, use_offset=True, *, text=None, dimensions=None,
            color=None, size=None,
    ):
        """Draw the label with its line-box top at the current origin.

        ``draw_text`` places the baseline from measured font metrics, so every
        label (CJK, capitals, descenders) fills the same stable line box — no
        per-script nudge tables.
        """
        if text is None:
            text = self.text
        if size is None:
            size = self.text_size
        if dimensions is None:
            dimensions = from_text_get_dimensions(text, size)
        if color is None:
            color = self.text_color
        w, _h = dimensions
        self.draw_text(
            text, position=[0, 0], color=color_to_srgb(color), size=size,
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

    def gpu_draw_status_badge(
            self, use_offset=True, slot_width=None, *, info=None,
            badge_size=None,
    ):
        """Draw a compact status code; color carries severity, text carries cause."""
        if info is None:
            info = self.element_status_info
        if badge_size is None:
            badge_size = self.status_badge_size
        width, height = badge_size
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

    def gpu_draw_status_accent(self, center, width, height, *, info=None):
        if info is None:
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

            # BEYOND: hover fill + softer active outline; CONFIRM: pressed fill.
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
                radius=self.text_radius,
                width=w + wm * 2,
                height=h + hm * 2,
                line_width=line_width,
            )
            self.gpu_draw_status_accent(
                (0.0, 0.0), w + wm * 2.0, h + hm * 2.0,
            )

    def gpu_draw_numeric_field_frame(
            self,
            *,
            field_left: float,
            field_right: float,
            field_top: float,
            field_bottom: float,
            corner_mask=None,
    ):
        """Restore only the outer frame after the three numeric surfaces."""
        width = float(field_right) - float(field_left)
        height = float(field_top) - float(field_bottom)
        if width <= 0.0 or height <= 0.0:
            return
        stroke, line_width = self._outline_colors(
            active=self.is_active_direction and not self._in_extension_ui(),
        )
        self.draw_rounded_rectangle_outlined(
            ((field_left + field_right) * 0.5,
             (field_top + field_bottom) * 0.5),
            fill=(0.0, 0.0, 0.0, 0.0),
            stroke=stroke,
            radius=self.text_radius,
            width=width,
            height=height,
            line_width=line_width,
            corner_mask=corner_mask or (True, True, True, True),
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
        arrow_slot = self.numeric_arrow_slot(th)
        if arrow_slot:
            w += arrow_slot * 2.0
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

    Measure content only; outer margin (scaled via layout_margin) is chrome
    around the panel. Do not bake margin into content size.

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
        dh = separator_line_width(
            self.draw_property.dividing_line_height,
            self._element_ui_scale(),
        )
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
        margin_x, margin_y = self.layout_margin

        icon_size = label_h
        gap = icon_size * self._GAP_FRAC
        chevron_size = icon_size * self._CHEVRON_FRAC
        row_h = max(
            icon_size * (1.0 + self._ROW_INTERVAL),
            icon_size + float(margin_y) * 2.0,
        )

        has_icon_col = False
        has_chevron_col = False
        has_number_arrows = False
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
            if item.numeric_arrows_visible:
                has_number_arrows = True

        # Content width = columns only (old code always added icon*2 even when unused).
        content_w = label_w
        if status_col_w:
            content_w += status_col_w + gap
        if has_icon_col:
            content_w += icon_size + gap
        if has_chevron_col:
            content_w += gap + chevron_size
        number_arrow_slot = number_arrow_slot_width(row_h) if has_number_arrows else 0.0
        if number_arrow_slot:
            content_w += number_arrow_slot * 2.0

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

        mx, my = margin_x, margin_y  # scaled; outer layout chrome only

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
            has_number_arrows=has_number_arrows,
            number_arrow_slot=number_arrow_slot,
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

    def _uses_single_extension_surface(self) -> bool:
        items = self.extension_items
        return bool(
            len(items) == 1
            and not items[0].is_layout_container
            and not items[0].is_dividing_line
            and not getattr(items[0], 'is_label', False)
            and not items[0].numeric_arrows_visible
        )

    def draw_gpu_extension_item(self, ops):
        lay = self._compute_extension_layout()
        w = lay.content_w
        single_surface_item = self._uses_single_extension_surface()
        with gpu.matrix.push_pop():
            self.ops = ops
            draw_debug_point()
            self.draw_gpu_extension_margin(paint_surface=not single_surface_item)

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
                row_left, row_bottom, row_right, row_top = (
                    resolve_extension_row_bounds(
                        w,
                        row_h,
                        mx,
                        my,
                        fill_outer_surface=single_surface_item,
                    )
                )
                surface_w = row_right - row_left
                surface_h = row_top - row_bottom
                row_rect = get_current_2d_rect(
                    (row_left, row_bottom, row_right, row_top),
                )
                draw_ctx = getattr(getattr(ops, 'session', None), 'draw_ctx', None)
                mouse = getattr(draw_ctx, 'mouse_region', None) if draw_ctx is not None else None
                is_label = bool(getattr(item, 'is_label', False))
                if is_label:
                    item.extension_by_child_draw_area = None
                    item.property_decrement_draw_area = None
                    item.property_value_draw_area = None
                    item.property_increment_draw_area = None
                    hovered = False
                else:
                    from .extension_hit import publish_child_row_hit
                    hovered = publish_child_row_hit(item, ops, row_rect, mouse=mouse)
                    item.publish_numeric_arrow_areas(
                        row_rect,
                        row_h,
                    )
                if not is_label and item.numeric_arrows_visible:
                    self.draw_rounded_rectangle_area(
                        (w * 0.5, -row_h * 0.5),
                        color=item._property_background_color(active=False),
                        radius=min(self.text_radius, row_h * 0.5),
                        width=surface_w,
                        height=row_h,
                    )
                # Numeric property rows paint a slider fill over the soft range.
                fraction = (
                    item.display_property_fraction
                    if not is_label and item.is_property_display
                    else None
                )
                if fraction is not None and fraction > 0.0:
                    fill_w = max(2.0, surface_w * fraction)
                    left = w * 0.5 - surface_w * 0.5
                    self.draw_rounded_rectangle_area(
                        (left + fill_w * 0.5, -row_h * 0.5),
                        color=item._property_slider_color(),
                        radius=min(self.text_radius, row_h * 0.5, fill_w * 0.5),
                        width=fill_w,
                        height=row_h,
                    )
                is_error = (
                    item.element_status_info.status.is_error
                    if not is_label
                    else False
                )
                if (
                    not is_label
                    and (
                        single_surface_item
                        or is_error
                        or (hovered and not item.numeric_arrows_visible)
                    )
                ):
                    stroke, line_width = self._outline_colors(active=hovered)
                    self.draw_rounded_rectangle_outlined(
                        (w * 0.5, -row_h * 0.5),
                        fill=item.extension_background_color,
                        stroke=stroke,
                        radius=min(self.text_radius, surface_h * 0.5),
                        width=surface_w,
                        height=surface_h,
                        line_width=line_width,
                    )
                if not is_label:
                    item.gpu_draw_status_accent(
                        (w * 0.5, -row_h * 0.5), surface_w, surface_h,
                    )
                    item.gpu_draw_numeric_arrows(
                        w,
                        row_h,
                        field_left=row_left,
                        field_right=row_right,
                        draw_value=False,
                    )

                with gpu.matrix.push_pop():
                    # Vertically center the icon/text band inside the row.
                    gpu.matrix.translate((0, -((row_h - lay.icon_size) * 0.5)))

                    if item.numeric_arrows_visible:
                        cursor_x = row_left + lay.number_arrow_slot
                    else:
                        cursor_x = lay.number_arrow_slot if lay.has_number_arrows else 0.0
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
                        item.gpu_draw_label(
                            use_offset=False,
                            color=(
                                tuple(self.draw_property.text_default_color)
                                if is_label
                                else None
                            ),
                        )

                    # Row/column/box content is already rendered inline; the
                    # chevron is reserved for actual child-gesture flyouts.
                    if lay.has_chevron_col and item.is_child_gesture:
                        tex = Texture.get_texture("1")
                        if tex is not None:
                            s = lay.chevron_size
                            chev_x = w - s
                            y = -(lay.icon_size + s) * 0.5
                            self.draw_image([chev_x, y], s, s, texture=tex)

                if item.is_child_gesture and (
                        hovered or item in ops.extension_hover
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

    def draw_gpu_extension_margin(self, *, paint_surface=True):
        draw = self.draw_property
        lay = getattr(self, "_extension_layout_cache", None) or self._compute_extension_layout()
        w, h = lay.content_w, lay.content_h
        mx, my = lay.margin_x, lay.margin_y
        self.extension_draw_area = get_current_2d_rect(
            (-mx, -h - my, w + mx, my),
        )
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if session is not None:
            self._gesture_layout_token = session.layout_token

        if len(self.extension_items) == 0 or not paint_surface:
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
