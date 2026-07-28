"""Persistent menu runtime shared by the menu operator and unregister cleanup."""

from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Any

import bpy

from ..utils.blf_text import measure_text
from ..utils.color import color_to_srgb
from ..utils.gesture_items import get_gesture_extension_items, poll_context_fingerprint
from ..utils.public_gpu import PublicGpu, gpu_draw_begin, gpu_draw_end
from ..utils.region_mouse import find_window_region, mouse_in_window_region
from ..utils.layout_alignment import blend_layout_hover_color
from ..utils.number_arrows import (
    number_edge_color,
    NUMBER_HOVER_BLEND,
    NUMBER_PART_DECREMENT,
    NUMBER_PART_INCREMENT,
    NUMBER_PART_VALUE,
    NUMBER_PRESSED_BLEND,
    number_arrow_chevron,
    number_field_part,
    number_field_rects,
    number_part_direction,
    number_arrow_slot_width,
    show_number_arrows,
)
from ..element.element_status import ElementStatus, get_element_status_info


MENU_TRANSITION_SECONDS = 0.16
MENU_FRAME_SECONDS = 1.0 / 60.0


def _rgba(value, fallback, *, alpha=None):
    try:
        color = tuple(float(component) for component in value)
    except (TypeError, ValueError):
        color = fallback
    if len(color) == 3:
        color = (*color, 1.0)
    elif len(color) < 4:
        color = fallback
    if alpha is not None:
        color = (*color[:3], float(alpha))
    return color


def _point_in_rect(point, rect) -> bool:
    if point is None or rect is None:
        return False
    x, y = point
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def _element_identity(value) -> int:
    if value is None:
        return 0
    try:
        pointer = int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        pointer = 0
    if pointer:
        return pointer
    try:
        if getattr(value, 'bl_rna', None) is not None:
            return 0
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return 0
    return id(value)


def _same_element(first, second) -> bool:
    if first is second:
        return True
    first_key = _element_identity(first)
    second_key = _element_identity(second)
    return bool(first_key and first_key == second_key)


def _property_field_rect(rect, scale: float):
    """Inset a numeric field like the other menu rows and keep it square."""
    x1, y1, x2, y2 = rect
    inset = min(2.0 * max(0.5, float(scale)), max(0.0, (x2 - x1) * 0.2))
    vertical = inset * 0.5
    return (x1 + inset, y1 + vertical, x2 - inset, y2 - vertical)


def _smoothstep(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


def _alpha_scaled(color, factor: float):
    return (*color[:3], color[3] * min(1.0, max(0.0, factor)))


@dataclass
class MenuMetrics:
    scale: float
    font_size: float
    line_height: float
    row_height: float
    separator_height: float
    header_height: float
    pad_x: float
    gap: float
    radius: float
    min_width: float
    max_width: float
    flyout_gap: float
    border_width: float


@dataclass
class MenuColors:
    background: tuple
    header: tuple
    hover: tuple
    text: tuple
    text_hover: tuple
    text_disabled: tuple
    outline: tuple
    separator: tuple
    error: tuple
    warning: tuple
    row: tuple = (0.12, 0.12, 0.12, 0.96)
    pressed: tuple = (0.04, 0.16, 0.38, 1.0)


@dataclass
class MenuRow:
    element: Any
    label: str
    kind: str
    enabled: bool = True
    status_info: Any = None
    rect: tuple[float, float, float, float] | None = None
    decrement_rect: tuple[float, float, float, float] | None = None
    value_rect: tuple[float, float, float, float] | None = None
    increment_rect: tuple[float, float, float, float] | None = None
    enum_identifier: str = ''
    enum_active: bool = False


@dataclass
class MenuPanel:
    depth: int
    rows: list[MenuRow]
    title: str = ''
    parent_row: MenuRow | None = None
    rect: tuple[float, float, float, float] | None = None
    header_rect: tuple[float, float, float, float] | None = None
    close_rect: tuple[float, float, float, float] | None = None
    width: float = 0.0
    height: float = 0.0


class GestureMenuRuntime(PublicGpu):
    """GPU menu lifecycle and event-neutral layout state.

    This runtime deliberately does not inherit GestureHandle or use a
    GestureSession. It has no trajectory, timeout, dwell timer, or idle redraw.
    """

    _active_by_window = {}
    _active_by_area = {}
    _draw_handles = {}
    _tracks_session_menu_state = True

    @classmethod
    def _menu_context_instance(cls):
        """Return this runtime's menu for the current area.

        Keep this name distinct from ``GestureGpuDraw._context_instance``:
        the unified preview inherits both renderers, and normal MRO lookup
        would otherwise route the menu draw callback through the radial map.
        """
        area = getattr(bpy.context, 'area', None)
        if area is None:
            return None
        try:
            return cls._active_by_area.get(area.as_pointer())
        except ReferenceError:
            return None

    @classmethod
    def _draw_callback(cls):
        instance = cls._menu_context_instance()
        if instance is None or getattr(instance, '_menu_close_requested', False):
            return
        try:
            instance._draw_menu()
        except Exception as exc:
            instance._menu_last_draw_error = repr(exc)
            return

    @classmethod
    def redraw_gesture(cls, gesture) -> None:
        for instance in tuple(cls._active_by_window.values()):
            try:
                if instance.operator_gesture == gesture:
                    instance._menu_layout_dirty = True
                    instance._tag_menu_redraw()
            except (AttributeError, ReferenceError, RuntimeError):
                ...

    @classmethod
    def force_close_all(cls) -> None:
        for instance in tuple(cls._active_by_window.values()):
            try:
                from .runtime_tooltip import cancel_hover_tooltip

                instance._cancel_menu_animation_timer()
                cancel_hover_tooltip(
                    getattr(instance, '_menu_tooltip_state', None),
                )
                instance._menu_close_requested = True
                instance._tag_menu_redraw()
            except (AttributeError, ReferenceError, RuntimeError):
                ...
        cls._active_by_window.clear()
        cls._active_by_area.clear()
        cls._remove_draw_handlers()
        if cls._tracks_session_menu_state:
            try:
                from ..utils.session_state import SessionState

                SessionState.gesture_menu_active = False
            except ImportError:
                ...

    @classmethod
    def _remove_draw_handlers(cls) -> None:
        for space_cls, handle in tuple(cls._draw_handles.items()):
            try:
                space_cls.draw_handler_remove(handle, 'WINDOW')
            except (ReferenceError, RuntimeError, ValueError):
                ...
        cls._draw_handles.clear()

    def _register_menu_runtime(self, context) -> bool:
        area = context.area
        window = context.window
        space = getattr(context, 'space_data', None)
        if space is None:
            try:
                space = area.spaces.active
            except (AttributeError, ReferenceError, RuntimeError):
                space = None
        if area is None or window is None or space is None:
            return False
        try:
            window_key = window.as_pointer()
            area_key = area.as_pointer()
        except ReferenceError:
            return False

        previous = self._active_by_window.get(window_key)
        if previous is not None and previous is not self:
            previous._menu_close_requested = True
            previous._unregister_menu_runtime()

        space_cls = type(space)
        if space_cls not in self._draw_handles:
            try:
                self._draw_handles[space_cls] = space_cls.draw_handler_add(
                    self.__class__._draw_callback, (), 'WINDOW', 'POST_PIXEL',
                )
            except (AttributeError, RuntimeError, TypeError):
                return False

        self._active_by_window[window_key] = self
        self._active_by_area[area_key] = self
        self._menu_window_key = window_key
        self._menu_area_key = area_key
        if self._tracks_session_menu_state:
            from ..utils.session_state import SessionState

            SessionState.gesture_menu_active = True
        self._tag_menu_redraw()
        return True

    def _unregister_menu_runtime(self) -> None:
        from .runtime_tooltip import cancel_hover_tooltip

        self._cancel_menu_animation_timer()
        cancel_hover_tooltip(getattr(self, '_menu_tooltip_state', None))
        window_key = getattr(self, '_menu_window_key', None)
        area_key = getattr(self, '_menu_area_key', None)
        if window_key is not None and self._active_by_window.get(window_key) is self:
            self._active_by_window.pop(window_key, None)
        if area_key is not None and self._active_by_area.get(area_key) is self:
            self._active_by_area.pop(area_key, None)
        if not self._active_by_window:
            self._remove_draw_handlers()
        if self._tracks_session_menu_state:
            try:
                from ..utils.session_state import SessionState

                SessionState.gesture_menu_active = bool(self._active_by_window)
            except ImportError:
                ...
        self._tag_menu_redraw()

    def _tag_menu_redraw(self) -> None:
        """Redraw the GPU menu without waking the owner area's sidebar."""
        area = getattr(self, '_menu_area', None)
        try:
            region = find_window_region(area)
            if region is not None:
                region.tag_redraw()
        except ReferenceError:
            ...

    def _cancel_menu_animation_timer(self) -> None:
        timer = getattr(self, '_menu_animation_timer', None)
        self._menu_animation_timer = None
        self._menu_animation_serial = getattr(self, '_menu_animation_serial', 0) + 1
        if timer is None:
            return
        try:
            bpy.app.timers.unregister(timer)
        except (AttributeError, RuntimeError, ValueError):
            ...

    def _menu_animation_reveal(self, *, now=None) -> float:
        now = time.monotonic() if now is None else float(now)
        closing_at = float(getattr(self, '_menu_closing_at', 0.0) or 0.0)
        if closing_at > 0.0:
            start = float(getattr(self, '_menu_close_start_reveal', 1.0))
            return start * (
                1.0 - _smoothstep((now - closing_at) / MENU_TRANSITION_SECONDS)
            )
        opened_at = float(getattr(self, '_menu_opened_at', 0.0) or 0.0)
        if opened_at <= 0.0:
            return 1.0
        return _smoothstep((now - opened_at) / MENU_TRANSITION_SECONDS)

    def _schedule_menu_animation(self) -> None:
        self._cancel_menu_animation_timer()
        serial = self._menu_animation_serial

        def _animate(*_args):
            if getattr(self, '_menu_animation_serial', 0) != serial:
                return None
            try:
                reveal = self._menu_animation_reveal()
                self._tag_menu_redraw()
                if getattr(self, '_menu_closing_at', 0.0):
                    if reveal <= 0.001:
                        self._menu_close_requested = True
                        self._menu_animation_timer = None
                        return None
                elif reveal >= 0.999:
                    self._menu_animation_timer = None
                    return None
                return MENU_FRAME_SECONDS
            except (AttributeError, ReferenceError, RuntimeError):
                self._menu_animation_timer = None
                return None

        self._menu_animation_timer = _animate
        try:
            bpy.app.timers.register(_animate, first_interval=MENU_FRAME_SECONDS)
        except (AttributeError, RuntimeError, ValueError):
            self._menu_animation_timer = None
            if getattr(self, '_menu_closing_at', 0.0):
                self._menu_close_requested = True

    def _start_menu_open_animation(self) -> None:
        self._menu_close_requested = False
        self._menu_opened_at = time.monotonic()
        self._menu_closing_at = 0.0
        self._menu_close_start_reveal = 1.0
        self._schedule_menu_animation()
        self._tag_menu_redraw()

    def _begin_menu_close(self) -> bool:
        """Start an idempotent close animation without releasing the owner."""
        if getattr(self, '_menu_close_requested', False):
            return False
        if getattr(self, '_menu_closing_at', 0.0):
            return False
        now = time.monotonic()
        self._menu_close_start_reveal = self._menu_animation_reveal(now=now)
        self._menu_closing_at = now
        from .runtime_tooltip import cancel_hover_tooltip

        cancel_hover_tooltip(getattr(self, '_menu_tooltip_state', None))
        self._menu_hovered_row = None
        self._menu_hovered_part = None
        self._menu_pressed_row = None
        self._menu_pressed_part = None
        self._menu_hovered_close = False
        self._menu_enum_dropdown = None
        self._menu_drag_mouse = None
        self._menu_drag_button = None
        ensure_event_timer = getattr(self, '_ensure_menu_animation_event_timer', None)
        if callable(ensure_event_timer):
            ensure_event_timer()
        self._schedule_menu_animation()
        self._tag_menu_redraw()
        return True

    def _menu_header_hit(self, event) -> bool:
        self._ensure_layout()
        if not self._menu_panels:
            return False
        point = self._menu_mouse(event)
        root = self._menu_panels[0]
        return (
            _point_in_rect(point, root.header_rect)
            and not _point_in_rect(point, root.close_rect)
        )

    def _start_menu_drag(self, event, *, button: str) -> bool:
        point = self._menu_mouse(event)
        if point is None:
            return False
        self._ensure_layout()
        if getattr(self, '_menu_centered', False) and self._menu_panels:
            root_rect = self._menu_panels[0].rect
            self._menu_anchor = (root_rect[0], root_rect[3])
            self._menu_centered = False
        self._menu_drag_mouse = point
        self._menu_drag_button = button
        sync_tooltip = getattr(self, '_sync_menu_tooltip', None)
        if callable(sync_tooltip):
            sync_tooltip(None)
        return True

    def _move_menu_drag(self, event) -> bool:
        previous = getattr(self, '_menu_drag_mouse', None)
        if previous is None or event.type != 'MOUSEMOVE':
            return False
        point = self._menu_mouse(event)
        if point is None:
            return True
        anchor_x, anchor_y = self._menu_anchor
        self._menu_anchor = (
            anchor_x + point[0] - previous[0],
            anchor_y + point[1] - previous[1],
        )
        self._menu_drag_mouse = point
        self._menu_layout_dirty = True
        self._ensure_layout(force=True)
        self._tag_menu_redraw()
        return True

    def _finish_menu_drag(self, *, button: str) -> bool:
        if getattr(self, '_menu_drag_button', None) != button:
            return False
        self._menu_drag_mouse = None
        self._menu_drag_button = None
        return True

    @property
    def operator_gesture(self):
        gesture = getattr(self, '_menu_gesture_ref', None)
        if gesture is not None:
            try:
                gesture.name
                return gesture
            except ReferenceError:
                pass
        from ..utils.gesture_store import get_gestures

        gestures = get_gestures()
        if gestures is None:
            return None
        return gestures.get(getattr(self, 'gesture', ''))

    @property
    def direction_element(self):
        return None

    @property
    def distance(self):
        return 0.0

    @property
    def mouse_is_in_extension_any_area(self):
        return True

    def _menu_style(self) -> str:
        gesture = self.operator_gesture
        try:
            return gesture.menu_style if gesture is not None else 'PANEL'
        except (AttributeError, ReferenceError):
            return 'PANEL'

    def _menu_keep_open(self) -> bool:
        gesture = self.operator_gesture
        try:
            return bool(gesture is not None and gesture.menu_keep_open)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            # Old data and test doubles follow the new default.
            return True

    def _metrics(self) -> MenuMetrics:
        scale = max(0.5, float(bpy.context.preferences.view.ui_scale))
        style = self._menu_style()
        if style == 'COMPACT':
            font_size = 11.0 * scale
            row_pad = 5.0 * scale
            pad_x = 8.0 * scale
        else:
            font_size = 12.0 * scale
            row_pad = 7.0 * scale
            pad_x = 10.0 * scale
        _, line_height = measure_text('Ag', font_size)
        row_height = line_height + row_pad
        return MenuMetrics(
            scale=scale,
            font_size=font_size,
            line_height=line_height,
            row_height=row_height,
            separator_height=max(7.0 * scale, row_height * 0.34),
            header_height=row_height + (2.0 * scale if style == 'PANEL' else 0.0),
            pad_x=pad_x,
            gap=6.0 * scale,
            radius=4.0 * scale,
            min_width=(184.0 if style == 'COMPACT' else 208.0) * scale,
            max_width=440.0 * scale,
            flyout_gap=5.0 * scale,
            border_width=max(0.75, scale),
        )

    @staticmethod
    def _theme_widget(ui, name, fallback_name):
        return getattr(ui, name, None) or getattr(ui, fallback_name, None)

    def _colors(self) -> MenuColors:
        ui = bpy.context.preferences.themes[0].user_interface
        menu = self._theme_widget(ui, 'wcol_menu', 'wcol_regular')
        item = self._theme_widget(ui, 'wcol_menu_item', 'wcol_regular')
        regular = self._theme_widget(ui, 'wcol_regular', 'wcol_menu')
        background = _rgba(getattr(menu, 'inner', None), (0.08, 0.08, 0.08, 0.98))
        header = _rgba(getattr(regular, 'inner', None), (0.11, 0.11, 0.11, 1.0))
        hover = _rgba(getattr(item, 'inner_sel', None), (0.08, 0.32, 0.62, 1.0))
        text = _rgba(getattr(menu, 'text', None), (0.82, 0.82, 0.82, 1.0))
        text_hover = _rgba(getattr(item, 'text_sel', None), (1.0, 1.0, 1.0, 1.0))
        outline = _rgba(getattr(menu, 'outline', None), (0.22, 0.22, 0.22, 1.0))
        row = _rgba(getattr(regular, 'inner', None), header)
        pressed = blend_layout_hover_color(hover, background, 0.46)
        text_disabled = (*text[:3], 0.42)
        separator = (*outline[:3], 0.7)
        error = (0.72, 0.08, 0.06, 0.9)
        warning = (0.92, 0.48, 0.06, 0.95)
        try:
            from ..utils.public import get_pref

            draw = get_pref().draw_property
            background = _rgba(draw.overlay_background_color, background)
            header = _rgba(draw.overlay_header_color, header)
            row = _rgba(draw.background_operator_color, row)
            hover = _rgba(draw.interaction_hover_color, hover)
            pressed = _rgba(draw.interaction_pressed_color, pressed)
            text = _rgba(draw.text_default_color, text)
            text_hover = _rgba(draw.text_active_color, text_hover)
            text_disabled = _rgba(draw.text_disabled_color, text_disabled)
            outline = _rgba(draw.outline_color, outline)
            separator = _rgba(draw.dividing_line_color, separator)
            error = _rgba(draw.status_error_color, error)
            warning = _rgba(draw.status_warning_color, warning)
        except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError):
            pass
        return MenuColors(
            background=background,
            header=header,
            hover=hover,
            text=text,
            text_hover=text_hover,
            text_disabled=text_disabled,
            outline=outline,
            separator=separator,
            error=error,
            warning=warning,
            row=row,
            pressed=pressed,
        )

    @staticmethod
    def _flatten_items(collection):
        try:
            items = get_gesture_extension_items(collection)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return []
        result = []
        for item in items:
            if item.is_layout_container:
                result.extend(GestureMenuRuntime._flatten_items(item.element))
            else:
                result.append(item)
        return result

    def _row_from_element(self, element) -> MenuRow:
        element.ops = self
        if element.is_dividing_line:
            return MenuRow(element, '', 'SEPARATOR', enabled=False)
        if element.is_property_display:
            info = get_element_status_info(element, ops=self)
            label = element.display_property_text
            try:
                if element.display_property_type == 'ENUM':
                    label = element.name_translate
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                ...
            return MenuRow(
                element,
                label,
                'PROPERTY',
                enabled=info.status is ElementStatus.VALID,
                status_info=info,
            )
        if element.is_child_gesture:
            info = get_element_status_info(element, ops=self)
            return MenuRow(
                element,
                element.name_translate,
                'CHILD',
                enabled=info.status is ElementStatus.VALID,
                status_info=info,
            )
        if element.is_operator:
            info = get_element_status_info(element, ops=self)
            return MenuRow(
                element,
                element.name_translate,
                'OPERATOR',
                enabled=info.status is ElementStatus.VALID,
                status_info=info,
            )
        return MenuRow(element, element.name_translate, 'LABEL', enabled=False)

    def _make_rows(self, collection) -> list[MenuRow]:
        rows = [self._row_from_element(item) for item in self._flatten_items(collection)]
        if not rows:
            rows.append(MenuRow(None, 'No available items', 'EMPTY', enabled=False))
        return rows

    @staticmethod
    def _enum_items(element):
        try:
            resolved = element.resolve_property()
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            resolved = None
        if resolved is None:
            return ()
        _owner, rna_prop = resolved
        if getattr(rna_prop, 'type', None) != 'ENUM':
            return ()
        try:
            from bpy.app.translations import pgettext_iface
        except ImportError:
            # Lightweight unit-test hosts may expose RNA doubles without the
            # complete translations module. Blender always provides it.
            def pgettext_iface(text):
                return text
        try:
            return tuple(
                (
                    str(getattr(item, 'identifier', '') or ''),
                    pgettext_iface(str(getattr(item, 'name', '') or '')),
                )
                for item in rna_prop.enum_items
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return ()

    def _enum_choice_rows(self, element) -> list[MenuRow]:
        try:
            current = element.display_property_value
            editable = bool(element.display_property_is_editable)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            current = None
            editable = False
        rows = []
        for identifier, label in self._enum_items(element):
            if not identifier:
                rows.append(MenuRow(
                    element,
                    label,
                    'LABEL' if label else 'SEPARATOR',
                    enabled=False,
                ))
                continue
            rows.append(MenuRow(
                element,
                label or identifier,
                'ENUM_ITEM',
                enabled=editable,
                enum_identifier=identifier,
                enum_active=identifier == current,
            ))
        if not rows:
            rows.append(MenuRow(element, 'No available items', 'EMPTY', enabled=False))
        return rows

    def _layout_key(self):
        from ..utils.public_cache import PublicCache

        gesture = self.operator_gesture
        try:
            gesture_key = gesture.as_pointer() if gesture is not None else 0
        except (AttributeError, ReferenceError):
            gesture_key = 0
        area = getattr(self, '_menu_area', None)
        region = find_window_region(area)
        region_size = (
            int(getattr(region, 'width', 0)),
            int(getattr(region, 'height', 0)),
        )
        return (
            gesture_key,
            PublicCache.__structure_generation__,
            PublicCache.__derived_generation__,
            poll_context_fingerprint(),
            self._menu_style(),
            _element_identity(getattr(self, '_menu_enum_dropdown', None)),
            bool(getattr(self, '_menu_centered', False)),
            tuple(getattr(self, '_menu_anchor', (0.0, 0.0))),
            region_size,
            tuple(id(item) for item in getattr(self, '_menu_open_path', ())),
        )

    def _ensure_layout(self, *, force=False) -> None:
        key = self._layout_key()
        if not force and not self._menu_layout_dirty and key == self._menu_layout_key:
            return
        self._menu_layout_key = key
        self._menu_layout_dirty = False
        self._build_panels()

    def _panel_size(self, panel, metrics) -> tuple[float, float]:
        widest = 0.0
        height = metrics.header_height if panel.depth == 0 else 0.0
        for row in panel.rows:
            if row.kind == 'SEPARATOR':
                height += metrics.separator_height
                continue
            width, _line = measure_text(row.label, metrics.font_size)
            if row.kind == 'ENUM_ITEM':
                width += metrics.line_height + metrics.gap
            if row.kind == 'PROPERTY':
                try:
                    prop_type = row.element.display_property_type or 'PROPERTY'
                except (AttributeError, ReferenceError, RuntimeError, TypeError):
                    prop_type = 'PROPERTY'
                control_width = self._property_control_width(prop_type, metrics, row)
                if self._numeric_arrows_visible(row, prop_type):
                    width += control_width * 2.0
                elif control_width:
                    width += control_width + metrics.gap
            badge = getattr(row.status_info, 'badge', '') if row.status_info is not None else ''
            if badge:
                badge_w, _line = measure_text(badge, metrics.font_size * 0.72)
                width += badge_w + metrics.gap * 2.0
            widest = max(widest, width)
            height += metrics.row_height
        if panel.title:
            title_w, _line = measure_text(panel.title, metrics.font_size)
            widest = max(widest, title_w + metrics.header_height)
        width = widest + metrics.pad_x * 2.0
        if any(row.kind == 'CHILD' for row in panel.rows):
            width += metrics.row_height * 0.65
        if any(row.element is not None and getattr(row.element, 'is_draw_icon', False) for row in panel.rows):
            width += metrics.line_height + metrics.gap
        return min(metrics.max_width, max(metrics.min_width, width)), height

    def _place_panel(self, panel, x, top, region, metrics) -> None:
        width, height = self._panel_size(panel, metrics)
        margin = 8.0 * metrics.scale
        x = min(max(margin, x), max(margin, region.width - width - margin))
        top = min(region.height - margin, max(height + margin, top))
        panel.width = width
        panel.height = height
        panel.rect = (x, top - height, x + width, top)

        cursor = top
        if panel.depth == 0:
            panel.header_rect = (x, cursor - metrics.header_height, x + width, cursor)
            close_size = metrics.header_height
            panel.close_rect = (x + width - close_size, cursor - close_size, x + width, cursor)
            cursor -= metrics.header_height
        for row in panel.rows:
            height_row = metrics.separator_height if row.kind == 'SEPARATOR' else metrics.row_height
            row.rect = (x, cursor - height_row, x + width, cursor)
            cursor -= height_row

    def _build_panels(self) -> None:
        hovered_element = getattr(
            getattr(self, '_menu_hovered_row', None),
            'element',
            None,
        )
        pressed_element = getattr(
            getattr(self, '_menu_pressed_row', None),
            'element',
            None,
        )
        gesture = self.operator_gesture
        area = getattr(self, '_menu_area', None)
        region = find_window_region(area)
        if gesture is None or region is None:
            self._menu_panels = []
            return

        metrics = self._metrics()
        root = MenuPanel(0, self._make_rows(gesture.element), title=gesture.name_translate)
        if getattr(self, '_menu_centered', False):
            root_w, root_h = self._panel_size(root, metrics)
            root_x = (float(region.width) - root_w) * 0.5
            root_top = (float(region.height) + root_h) * 0.5
            self._place_panel(root, root_x, root_top, region, metrics)
        else:
            anchor = self._menu_anchor
            self._place_panel(root, anchor[0], anchor[1], region, metrics)
        panels = [root]

        valid_path = []
        parent_panel = root
        for depth, child in enumerate(tuple(self._menu_open_path)[:8], start=1):
            parent_row = next(
                (row for row in parent_panel.rows if row.element == child and row.kind == 'CHILD'),
                None,
            )
            if parent_row is None or parent_row.rect is None:
                break
            panel = MenuPanel(depth, self._make_rows(child.element), parent_row=parent_row)
            panel_w, _panel_h = self._panel_size(panel, metrics)
            px1, _py1, px2, _py2 = parent_panel.rect
            rx1, _ry1, _rx2, ry2 = parent_row.rect
            x = px2 + metrics.flyout_gap
            if x + panel_w > region.width - 8.0 * metrics.scale:
                x = px1 - metrics.flyout_gap - panel_w
            self._place_panel(panel, x, ry2, region, metrics)
            panels.append(panel)
            valid_path.append(child)
            parent_panel = panel
        self._menu_open_path = valid_path

        dropdown = getattr(self, '_menu_enum_dropdown', None)
        if dropdown is not None:
            owner_panel = None
            owner_row = None
            for candidate_panel in panels:
                candidate_row = next(
                    (
                        row for row in candidate_panel.rows
                        if row.kind == 'PROPERTY'
                        and _same_element(row.element, dropdown)
                    ),
                    None,
                )
                if candidate_row is not None:
                    owner_panel = candidate_panel
                    owner_row = candidate_row
                    break
            if owner_panel is None or owner_row is None or owner_row.rect is None:
                self._menu_enum_dropdown = None
            else:
                panel = MenuPanel(
                    owner_panel.depth + 1,
                    self._enum_choice_rows(dropdown),
                    parent_row=owner_row,
                )
                panel_w, _panel_h = self._panel_size(panel, metrics)
                px1, _py1, px2, _py2 = owner_panel.rect
                _rx1, _ry1, _rx2, ry2 = owner_row.rect
                x = px2 + metrics.flyout_gap
                if x + panel_w > region.width - 8.0 * metrics.scale:
                    x = px1 - metrics.flyout_gap - panel_w
                self._place_panel(panel, x, ry2, region, metrics)
                panels.append(panel)
        self._menu_panels = panels
        rows = tuple(row for panel in panels for row in panel.rows)
        if hovered_element is not None:
            self._menu_hovered_row = next(
                (row for row in rows if row.element == hovered_element),
                None,
            )
            if self._menu_hovered_row is None:
                self._menu_hovered_part = None
        if pressed_element is not None:
            self._menu_pressed_row = next(
                (row for row in rows if row.element == pressed_element),
                None,
            )
            if self._menu_pressed_row is None:
                self._menu_pressed_part = None

    def _draw_panel_background(self, panel, metrics, colors) -> None:
        x1, y1, x2, y2 = panel.rect
        width = x2 - x1
        height = y2 - y1
        center = (x1 + width * 0.5, y1 + height * 0.5)
        style = self._menu_style()
        if style == 'BORDERLESS':
            self.draw_rounded_rectangle_area(
                center,
                color=colors.background,
                radius=metrics.radius,
                width=width,
                height=height,
            )
        else:
            self.draw_rounded_rectangle_outlined(
                center,
                fill=colors.background,
                stroke=colors.outline,
                radius=metrics.radius,
                width=width,
                height=height,
                line_width=metrics.border_width,
            )

    def _draw_header(self, panel, metrics, colors) -> None:
        if panel.header_rect is None:
            return
        x1, y1, x2, y2 = panel.header_rect
        width = x2 - x1
        height = y2 - y1
        self.draw_rounded_rectangle_area(
            (x1 + width * 0.5, y1 + height * 0.5),
            color=colors.header,
            radius=metrics.radius,
            width=width,
            height=height,
        )
        # Retain only the title bar's top corners; its lower edge joins the body.
        self.draw_rectangle(x1, y1, width, min(metrics.radius, height * 0.5), colors.header)
        title = self._fit_text(
            panel.title,
            max(1.0, width - metrics.pad_x * 2.0 - height),
            metrics.font_size,
        )
        self.draw_text(
            title,
            position=(x1 + metrics.pad_x, y2 - (height - metrics.line_height) * 0.5),
            size=metrics.font_size,
            color=color_to_srgb(colors.text),
        )
        if panel.close_rect is not None:
            cx1, cy1, cx2, cy2 = panel.close_rect
            close_pressed = bool(getattr(self, '_menu_pressed_close', False))
            close_hovered = bool(getattr(self, '_menu_hovered_close', False))
            if close_pressed or close_hovered:
                close_color = colors.pressed if close_pressed else colors.hover
                self.draw_rounded_rectangle_area(
                    ((cx1 + cx2) * 0.5, (cy1 + cy2) * 0.5),
                    color=close_color,
                    radius=metrics.radius,
                    width=cx2 - cx1,
                    height=cy2 - cy1,
                    corner_mask=(False, True, False, False),
                )
            inset = height * 0.34
            close_text = colors.text_hover if close_pressed or close_hovered else colors.text
            self.draw_2d_line(
                ((cx1 + inset, cy1 + inset), (cx2 - inset, cy2 - inset)),
                color=close_text,
                line_width=max(1.0, 1.2 * metrics.scale),
            )
            self.draw_2d_line(
                ((cx1 + inset, cy2 - inset), (cx2 - inset, cy1 + inset)),
                color=close_text,
                line_width=max(1.0, 1.2 * metrics.scale),
            )

    def _property_visual(self, row, colors):
        element = row.element
        try:
            prop_type = element.display_property_type or 'PROPERTY'
            value = element.display_property_value
            fraction = element.display_property_fraction
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            prop_type, value, fraction = 'PROPERTY', None, None
        try:
            from ..utils.public import get_pref

            draw = get_pref().draw_property
        except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError):
            draw = None

        reveal = float(getattr(self, '_menu_current_reveal', 1.0))
        if prop_type == 'BOOLEAN':
            fallback = colors.hover if value else colors.header
            source = getattr(
                draw,
                'background_bool_true' if value else 'background_bool_false',
                fallback,
            )
            base = _rgba(source, fallback)
            active = _rgba(getattr(draw, 'background_bool_true', colors.hover), colors.hover)
        elif prop_type == 'INT':
            base = _rgba(getattr(draw, 'background_int_color', colors.header), colors.header)
            active = _rgba(
                getattr(draw, 'background_int_active_color', colors.hover),
                colors.hover,
            )
        elif prop_type == 'FLOAT':
            base = _rgba(getattr(draw, 'background_float_color', colors.header), colors.header)
            active = _rgba(
                getattr(draw, 'background_float_active_color', colors.hover),
                colors.hover,
            )
        else:
            base = _rgba(
                getattr(draw, 'background_operator_color', colors.header),
                colors.header,
            )
            active = _rgba(
                getattr(draw, 'background_operator_active_color', colors.hover),
                colors.hover,
            )
        return (
            prop_type,
            value,
            fraction,
            _alpha_scaled(base, reveal),
            _alpha_scaled(active, reveal),
        )

    @staticmethod
    def _numeric_arrows_visible(row, prop_type) -> bool:
        if prop_type not in {'INT', 'FLOAT'} or not show_number_arrows():
            return False
        if row is None or not row.enabled:
            return False
        try:
            return bool(row.element.display_property_is_editable)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    @classmethod
    def _property_control_width(cls, prop_type, metrics, row=None) -> float:
        if cls._numeric_arrows_visible(row, prop_type):
            return number_arrow_slot_width(metrics.row_height)
        if prop_type == 'BOOLEAN':
            return 0.0
        if prop_type == 'ENUM':
            label_width = measure_text(cls._enum_value_label(row), metrics.font_size)[0]
            arrow_width = max(8.0 * metrics.scale, metrics.gap * 1.25)
            return min(
                metrics.max_width * 0.52,
                label_width + arrow_width + metrics.gap * 2.0,
            )
        badge = {
            'INT': 'INT',
            'FLOAT': 'FLOAT',
            'ENUM': 'ENUM',
            'STRING': 'TEXT',
        }.get(prop_type, 'PROP')
        return measure_text(badge, metrics.font_size * 0.62)[0] + metrics.gap * 1.5

    @classmethod
    def _enum_value_label(cls, row) -> str:
        if row is None or row.element is None:
            return ''
        try:
            current = row.element.display_property_value
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return '?'
        for identifier, label in cls._enum_items(row.element):
            if identifier == current:
                return label or identifier
        return str(current) if current is not None else '?'

    @staticmethod
    def _show_boolean_state_icon(row) -> bool:
        """Respect the per-property icon choice for persistent menu rows."""
        try:
            return bool(row.element.property_bool_icons_enabled)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    def _draw_boolean_state_icon(self, row, *, x, y1, height, metrics) -> float:
        """Draw Blender's checkbox treatment and return its occupied width."""
        try:
            from ..utils.texture import Texture

            icon = 'CHECKBOX_HLT' if row.element.display_property_value else 'CHECKBOX_DEHLT'
            texture = Texture.get_texture(icon)
        except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError, TypeError):
            texture = None
        if texture is None:
            return 0.0
        icon_size = min(metrics.line_height, height - 4.0 * metrics.scale)
        self.draw_image(
            (x, y1 + (height - icon_size) * 0.5),
            icon_size,
            icon_size,
            texture=texture,
        )
        return icon_size + metrics.gap

    def _draw_property_control(
            self,
            visual,
            *,
            row,
            x1,
            x2,
            y1,
            y2,
            metrics,
            colors,
    ) -> None:
        prop_type, value, _fraction, base, active = visual
        height = y2 - y1
        if self._numeric_arrows_visible(row, prop_type):
            slot = number_arrow_slot_width(height)
            field_rect = _property_field_rect(
                (x1, y1, x2, y2),
                metrics.scale,
            )
            (
                row.decrement_rect,
                row.value_rect,
                row.increment_rect,
            ) = number_field_rects(
                field_rect,
                slot,
            )
            hovered_part = (
                getattr(self, '_menu_hovered_part', None)
                if row is getattr(self, '_menu_hovered_row', None)
                else None
            )
            pressed_part = (
                getattr(self, '_menu_pressed_part', None)
                if row is getattr(self, '_menu_pressed_row', None)
                else None
            )
            part_rects = (
                (
                    NUMBER_PART_DECREMENT,
                    row.decrement_rect,
                ),
                (
                    NUMBER_PART_VALUE,
                    row.value_rect,
                ),
                (
                    NUMBER_PART_INCREMENT,
                    row.increment_rect,
                ),
            )
            for part, rect in part_rects:
                if rect is None:
                    continue
                rx1, ry1, rx2, ry2 = rect
                if part == pressed_part:
                    amount = NUMBER_PRESSED_BLEND
                    target = colors.pressed
                elif part == hovered_part:
                    amount = NUMBER_HOVER_BLEND
                    target = colors.hover
                elif part == NUMBER_PART_VALUE:
                    continue
                else:
                    state_color = number_edge_color(base)
                    self.draw_rectangle(
                        rx1,
                        ry1,
                        max(1.0, rx2 - rx1),
                        max(1.0, ry2 - ry1),
                        state_color,
                    )
                    continue
                state_color = blend_layout_hover_color(base, target, amount)
                self.draw_rectangle(
                    rx1,
                    ry1,
                    max(1.0, rx2 - rx1),
                    max(1.0, ry2 - ry1),
                    state_color,
                )

            center_y = (y1 + y2) * 0.5
            half_w, half_h, line_width = number_arrow_chevron(height, slot)
            for part, center_x, direction in (
                (
                    NUMBER_PART_DECREMENT,
                    field_rect[0] + slot * 0.5,
                    -1,
                ),
                (
                    NUMBER_PART_INCREMENT,
                    field_rect[2] - slot * 0.5,
                    1,
                ),
            ):
                tip_x = center_x + direction * half_w
                back_x = center_x - direction * half_w
                arrow_color = (
                    colors.text_hover
                    if part in {hovered_part, pressed_part}
                    else colors.text
                )
                self.draw_2d_line(
                    ((back_x, center_y + half_h), (tip_x, center_y)),
                    color=arrow_color,
                    line_width=line_width,
                )
                self.draw_2d_line(
                    ((tip_x, center_y), (back_x, center_y - half_h)),
                    color=arrow_color,
                    line_width=line_width,
                )
            return
        row.decrement_rect = None
        row.value_rect = None
        row.increment_rect = None
        if prop_type == 'BOOLEAN':
            return

        if prop_type == 'ENUM':
            label = self._enum_value_label(row)
            control_width = self._property_control_width(prop_type, metrics, row)
            right = x2 - 2.0 * metrics.scale
            left = max(x1 + metrics.pad_x, right - control_width)
            is_open = _same_element(
                row.element,
                getattr(self, '_menu_enum_dropdown', None),
            )
            control_color = blend_layout_hover_color(
                base,
                active,
                0.58 if is_open else 0.22,
            )
            self.draw_rounded_rectangle_area(
                ((left + right) * 0.5, (y1 + y2) * 0.5),
                color=control_color,
                radius=min(2.0 * metrics.scale, height * 0.18),
                width=max(1.0, right - left),
                height=max(1.0, height - 2.0 * metrics.scale),
            )
            arrow_span = max(3.0 * metrics.scale, metrics.gap * 0.45)
            arrow_x = right - metrics.gap
            arrow_y = (y1 + y2) * 0.5
            self.draw_2d_line(
                (
                    (arrow_x - arrow_span, arrow_y + arrow_span * 0.45),
                    (arrow_x, arrow_y - arrow_span * 0.45),
                    (arrow_x + arrow_span, arrow_y + arrow_span * 0.45),
                ),
                color=colors.text_hover if is_open else colors.text,
                line_width=max(1.0, metrics.scale),
            )
            text_right = arrow_x - arrow_span - metrics.gap * 0.5
            fitted = self._fit_text(
                label,
                max(1.0, text_right - left - metrics.gap),
                metrics.font_size,
            )
            self.draw_text(
                fitted,
                position=(left + metrics.gap, y2 - (height - metrics.line_height) * 0.5),
                size=metrics.font_size,
                color=color_to_srgb(colors.text_hover if is_open else colors.text),
            )
            return

        badge = {
            'INT': 'INT',
            'FLOAT': 'FLOAT',
            'ENUM': 'ENUM',
            'STRING': 'TEXT',
        }.get(prop_type, 'PROP')
        size = metrics.font_size * 0.62
        badge_w, _line = measure_text(badge, size)
        badge_h = max(9.0 * metrics.scale, height * 0.46)
        right = x2 - metrics.pad_x
        left = right - badge_w - metrics.gap
        self.draw_rounded_rectangle_area(
            ((left + right) * 0.5, (y1 + y2) * 0.5),
            color=active,
            radius=badge_h * 0.5,
            width=right - left,
            height=badge_h,
        )
        self.draw_text(
            badge,
            position=(left + metrics.gap * 0.5, y2 - (height - metrics.line_height) * 0.5),
            size=size,
            color=color_to_srgb(colors.text_hover),
        )

    def _draw_row(self, row, metrics, colors) -> None:
        x1, y1, x2, y2 = row.rect
        width = x2 - x1
        height = y2 - y1
        if row.kind == 'SEPARATOR':
            y = y1 + height * 0.5
            inset = metrics.pad_x
            self.draw_2d_line(
                ((x1 + inset, y), (x2 - inset, y)),
                color=colors.separator,
                line_width=max(0.75, metrics.scale * 0.8),
            )
            return

        hovered = row is getattr(self, '_menu_hovered_row', None)
        pressed = row is getattr(self, '_menu_pressed_row', None)
        status = getattr(row.status_info, 'status', ElementStatus.VALID)
        property_visual = self._property_visual(row, colors) if row.kind == 'PROPERTY' else None
        has_number_field = bool(
            property_visual is not None
            and self._numeric_arrows_visible(row, property_visual[0])
        )
        has_boolean_icon = (
            property_visual is not None
            and property_visual[0] == 'BOOLEAN'
            and self._show_boolean_state_icon(row)
        )
        has_property_background = (
            property_visual is not None
            and (property_visual[0] != 'BOOLEAN' or has_boolean_icon)
        )
        is_surface = row.kind in {'OPERATOR', 'PROPERTY', 'CHILD', 'ENUM_ITEM'}
        if status.is_error or has_property_background or is_surface:
            inset = 0.0 if has_number_field else 2.0 * metrics.scale
            if status.is_error:
                row_color = colors.error
            elif property_visual is not None:
                row_color = (
                    property_visual[3]
                    if has_property_background
                    else colors.row
                )
                if pressed and row.enabled:
                    row_color = blend_layout_hover_color(row_color, colors.pressed, 0.90)
                elif hovered and row.enabled:
                    row_color = blend_layout_hover_color(row_color, colors.hover, 0.72)
            else:
                if pressed and row.enabled:
                    row_color = colors.pressed
                elif hovered and row.enabled:
                    row_color = colors.hover
                elif row.enabled:
                    row_color = colors.row
                else:
                    row_color = (*colors.row[:3], colors.row[3] * 0.42)
            if has_number_field:
                fx1, fy1, fx2, fy2 = _property_field_rect(row.rect, metrics.scale)
                self.draw_rectangle(
                    fx1,
                    fy1,
                    max(1.0, fx2 - fx1),
                    max(1.0, fy2 - fy1),
                    row_color,
                )
            else:
                self.draw_rounded_rectangle_area(
                    (x1 + width * 0.5, y1 + height * 0.5),
                    color=row_color,
                    radius=max(1.0, metrics.radius - inset),
                    width=max(1.0, width - inset * 2.0),
                    height=max(1.0, height - inset),
                )
            if property_visual is not None and not status.is_error:
                fraction = property_visual[2]
                if fraction is not None and fraction > 0.0:
                    fill_w = max(2.0, (width - inset * 2.0) * fraction)
                    fill_color = property_visual[4]
                    if pressed and row.enabled:
                        fill_color = blend_layout_hover_color(fill_color, colors.pressed, 0.90)
                    elif hovered and row.enabled:
                        fill_color = blend_layout_hover_color(fill_color, colors.hover, 0.72)
                    if has_number_field:
                        fx1, fy1, fx2, fy2 = _property_field_rect(row.rect, metrics.scale)
                        fill_w = max(2.0, (fx2 - fx1) * fraction)
                        self.draw_rectangle(
                            fx1,
                            fy1,
                            fill_w,
                            max(1.0, fy2 - fy1),
                            fill_color,
                        )
                    else:
                        self.draw_rounded_rectangle_area(
                            (x1 + inset + fill_w * 0.5, y1 + height * 0.5),
                            color=fill_color,
                            radius=max(1.0, metrics.radius - inset),
                            width=fill_w,
                            height=max(1.0, height - inset),
                        )
        if status is not ElementStatus.VALID:
            marker_color = colors.text_hover if status.is_error else colors.warning
            marker_w = max(2.0, 2.0 * metrics.scale)
            self.draw_rectangle(
                x1 + 2.0 * metrics.scale,
                y1 + 2.0,
                marker_w,
                height - 4.0,
                marker_color,
            )

        if status.is_error:
            text_color = colors.text_hover
        elif (hovered or pressed) and row.enabled:
            text_color = colors.text_hover
        else:
            text_color = colors.text if row.enabled else colors.text_disabled
        cursor_x = x1 + metrics.pad_x
        if row.kind == 'ENUM_ITEM':
            circle_radius = max(3.0 * metrics.scale, metrics.line_height * 0.24)
            center = (cursor_x + circle_radius, y1 + height * 0.5)
            self.draw_circle(
                center,
                circle_radius,
                color=text_color,
                line_width=max(1.0, metrics.scale),
            )
            if row.enum_active:
                inner_radius = circle_radius * 0.48
                self.draw_rounded_rectangle_area(
                    center,
                    color=text_color,
                    radius=inner_radius,
                    width=inner_radius * 2.0,
                    height=inner_radius * 2.0,
                )
            cursor_x += circle_radius * 2.0 + metrics.gap
        if has_boolean_icon:
            cursor_x += self._draw_boolean_state_icon(
                row,
                x=cursor_x,
                y1=y1,
                height=height,
                metrics=metrics,
            )
        if (
                property_visual is not None
                and self._numeric_arrows_visible(row, property_visual[0])
        ):
            cursor_x += number_arrow_slot_width(height)
        element = row.element
        if element is not None and getattr(element, 'is_draw_icon', False):
            try:
                from ..utils.texture import Texture

                texture = Texture.get_texture(element._gpu_draw_icon_name())
                if texture is not None:
                    icon_size = metrics.line_height
                    self.draw_image(
                        (cursor_x, y1 + (height - icon_size) * 0.5),
                        icon_size,
                        icon_size,
                        texture=texture,
                    )
                    cursor_x += icon_size + metrics.gap
            except (AttributeError, KeyError, ReferenceError, RuntimeError):
                ...
        right_reserve = metrics.pad_x
        if property_visual is not None:
            right_reserve += self._property_control_width(
                property_visual[0],
                metrics,
                row,
            )
        badge = getattr(row.status_info, 'badge', '') if row.status_info is not None else ''
        if row.kind == 'CHILD':
            right_reserve += metrics.row_height * 0.65
        if badge:
            badge_size = metrics.font_size * 0.72
            badge_w, _line = measure_text(badge, badge_size)
            badge_color = colors.text_hover if status.is_error else colors.warning
            self.draw_text(
                badge,
                position=(x2 - right_reserve - badge_w, y2 - (height - metrics.line_height) * 0.5),
                size=badge_size,
                color=color_to_srgb(badge_color),
            )
            right_reserve += badge_w + metrics.gap
        max_text_width = max(1.0, x2 - right_reserve - cursor_x)
        label = self._fit_text(row.label, max_text_width, metrics.font_size)
        self.draw_text(
            label,
            position=(cursor_x, y2 - (height - metrics.line_height) * 0.5),
            size=metrics.font_size,
            color=color_to_srgb(text_color),
        )
        if row.kind == 'CHILD':
            arrow = '>'
            arrow_w, _line = measure_text(arrow, metrics.font_size)
            self.draw_text(
                arrow,
                position=(x2 - metrics.pad_x - arrow_w, y2 - (height - metrics.line_height) * 0.5),
                size=metrics.font_size,
                color=color_to_srgb(text_color),
            )
        if property_visual is not None:
            self._draw_property_control(
                property_visual,
                row=row,
                x1=x1,
                x2=x2,
                y1=y1,
                y2=y2,
                metrics=metrics,
                colors=colors,
            )

    @staticmethod
    def _fit_text(text: str, max_width: float, size: float) -> str:
        if measure_text(text, size)[0] <= max_width:
            return text
        suffix = '...'
        suffix_width = measure_text(suffix, size)[0]
        if suffix_width >= max_width:
            return suffix
        low = 0
        high = len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if measure_text(text[:middle], size)[0] + suffix_width <= max_width:
                low = middle
            else:
                high = middle - 1
        return text[:low] + suffix

    def _draw_menu(self) -> None:
        area = getattr(self, '_menu_area', None)
        if area is not None and bpy.context.area != area:
            return
        region = find_window_region(area)
        if region is None:
            return
        self._ensure_layout()
        if not self._menu_panels:
            return
        reveal = self._menu_animation_reveal()
        if reveal <= 0.0:
            return
        metrics = self._metrics()
        base_colors = self._colors()
        colors = replace(
            base_colors,
            **{
                field: _alpha_scaled(getattr(base_colors, field), reveal)
                for field in MenuColors.__dataclass_fields__
            },
        )
        self._menu_current_reveal = reveal
        gpu_draw_begin()
        try:
            for panel in self._menu_panels:
                self._draw_panel_background(panel, metrics, colors)
                self._draw_header(panel, metrics, colors)
                for row in panel.rows:
                    self._draw_row(row, metrics, colors)
            if not getattr(self, '_menu_closing_at', 0.0):
                self._draw_hover_annotation(metrics, colors, region)
        finally:
            gpu_draw_end()
        self._menu_draw_count += 1

    def _draw_hover_annotation(self, metrics, colors, region) -> None:
        """Show delayed source metadata and diagnostics for the hovered row."""
        state = getattr(self, '_menu_tooltip_state', None)
        from .runtime_tooltip import tooltip_draw_data

        element, tooltip, reveal = tooltip_draw_data(state)
        row = next(
            (
                candidate
                for panel in self._menu_panels
                for candidate in panel.rows
                if candidate.element is element
            ),
            None,
        )
        if row is None or tooltip is None:
            return
        if reveal <= 0.0:
            return
        if tooltip.color_role == 'error':
            accent = colors.error
        elif tooltip.color_role == 'warning':
            accent = colors.warning
        elif tooltip.color_role == 'disabled':
            accent = colors.text_disabled
        else:
            accent = colors.hover
        metadata = (*colors.text[:3], colors.text[3] * 0.38)
        self.draw_runtime_tooltip(
            tooltip,
            anchor_rect=row.rect,
            viewport_size=(region.width, region.height),
            size=max(10.0, metrics.font_size * 0.92),
            scale=metrics.scale,
            fill=colors.background,
            stroke=accent,
            text_color=color_to_srgb(colors.text),
            metadata_color=color_to_srgb(metadata),
            issue_color=color_to_srgb(accent),
            reveal=reveal,
        )

    def _menu_mouse(self, event):
        return mouse_in_window_region(event, getattr(self, '_menu_area', None))

    def _menu_contains(self, point) -> bool:
        return any(_point_in_rect(point, panel.rect) for panel in self._menu_panels)

    @staticmethod
    def _is_enum_property_row(row) -> bool:
        if row is None or row.kind != 'PROPERTY' or not row.enabled:
            return False
        try:
            return row.element.display_property_type == 'ENUM'
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    def _toggle_menu_enum_dropdown(self, row) -> bool:
        if not self._is_enum_property_row(row):
            return False
        current = getattr(self, '_menu_enum_dropdown', None)
        self._menu_enum_dropdown = (
            None if _same_element(current, row.element) else row.element
        )
        self._menu_layout_dirty = True
        self._ensure_layout(force=True)
        self._tag_menu_redraw()
        return True

    def _close_menu_enum_dropdown(self) -> bool:
        if getattr(self, '_menu_enum_dropdown', None) is None:
            return False
        self._menu_enum_dropdown = None
        self._menu_layout_dirty = True
        self._ensure_layout(force=True)
        self._tag_menu_redraw()
        return True

    def _set_menu_enum_choice(self, row) -> bool:
        if row is None or row.kind != 'ENUM_ITEM' or not row.enabled:
            return False
        try:
            changed = row.element.set_display_property_value(row.enum_identifier)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            changed = False
        self._menu_enum_dropdown = None
        self._menu_layout_dirty = True
        self._ensure_layout(force=True)
        if changed:
            self._menu_mark_context_changed()
        else:
            self._tag_menu_redraw()
        return True

    def _menu_number_part(self, row, point):
        if row is None or row.kind != 'PROPERTY' or not show_number_arrows():
            return None
        try:
            if row.element.display_property_type not in {'INT', 'FLOAT'}:
                return None
            if not row.element.display_property_is_editable:
                return None
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        if (
                row.decrement_rect is None
                or row.value_rect is None
                or row.increment_rect is None
        ):
            field_rect = _property_field_rect(
                row.rect,
                self._metrics().scale,
            )
            (
                row.decrement_rect,
                row.value_rect,
                row.increment_rect,
            ) = number_field_rects(
                field_rect,
                number_arrow_slot_width(row.rect[3] - row.rect[1]),
            )
        return number_field_part(
            point,
            row.decrement_rect,
            row.value_rect,
            row.increment_rect,
        )

    def _press_menu_row(self, row, event) -> bool:
        part = self._menu_number_part(row, self._menu_mouse(event))
        changed = (
            getattr(self, '_menu_pressed_row', None) is not row
            or getattr(self, '_menu_pressed_part', None) != part
        )
        self._menu_pressed_row = row
        self._menu_pressed_part = part
        return changed

    def _clear_menu_press(self) -> bool:
        if (
                getattr(self, '_menu_pressed_row', None) is None
                and getattr(self, '_menu_pressed_part', None) is None
                and not getattr(self, '_menu_pressed_close', False)
        ):
            return False
        self._menu_pressed_row = None
        self._menu_pressed_part = None
        self._menu_pressed_close = False
        return True

    def _update_menu_hover(self, event) -> bool:
        self._ensure_layout()
        point = self._menu_mouse(event)
        old_row = self._menu_hovered_row
        old_part = getattr(self, '_menu_hovered_part', None)
        old_close = bool(getattr(self, '_menu_hovered_close', False))
        hovered = None
        hovered_panel = None
        hovered_close = bool(
            self._menu_panels
            and _point_in_rect(point, self._menu_panels[0].close_rect)
        )
        if not hovered_close:
            for panel in reversed(self._menu_panels):
                for row in panel.rows:
                    if _point_in_rect(point, row.rect):
                        hovered = row
                        hovered_panel = panel
                        break
                if hovered is not None:
                    break

        self._menu_hovered_row = hovered
        self._menu_hovered_part = self._menu_number_part(hovered, point)
        self._menu_hovered_close = hovered_close
        tooltip_changed = self._sync_menu_tooltip(
            getattr(hovered, 'element', None) if hovered is not None else None
        )
        path_changed = False
        if hovered_panel is not None:
            keep = list(self._menu_open_path[:hovered_panel.depth])
            if hovered is not None and hovered.kind == 'CHILD':
                keep.append(hovered.element)
            if keep != self._menu_open_path:
                self._menu_open_path = keep
                self._menu_layout_dirty = True
                self._ensure_layout(force=True)
                path_changed = True
        return (
            old_row is not hovered
            or old_part != self._menu_hovered_part
            or old_close != hovered_close
            or path_changed
            or tooltip_changed
        )

    def _sync_menu_tooltip(self, element) -> bool:
        from .runtime_tooltip import HoverTooltipState, sync_hover_tooltip

        state = getattr(self, '_menu_tooltip_state', None)
        if state is None:
            state = HoverTooltipState()
            try:
                from ..utils.adapter import operator_setattr

                operator_setattr(self, '_menu_tooltip_state', state)
            except (AttributeError, ImportError, TypeError):
                self._menu_tooltip_state = state
        from ..utils.public import get_pref

        changed = sync_hover_tooltip(
            state,
            element,
            delay_ms=getattr(
                get_pref().gesture_property,
                'hover_tooltip_delay',
                300,
            ),
            redraw=self._tag_menu_redraw,
        )
        if not changed:
            return False
        if element is not None:
            from ..element.element_tooltip import build_runtime_tooltip

            state.tooltip = build_runtime_tooltip(
                element,
                preview_read_only=bool(getattr(self, 'preview_read_only', False)),
            )
            if state.tooltip is None:
                sync_hover_tooltip(
                    state,
                    None,
                    delay_ms=0,
                    redraw=self._tag_menu_redraw,
                )
        return True

    def _menu_close_hit(self, event) -> bool:
        if not self._menu_panels:
            return False
        return _point_in_rect(self._menu_mouse(event), self._menu_panels[0].close_rect)

    def _press_menu_close(self) -> bool:
        if getattr(self, '_menu_pressed_close', False):
            return False
        self._menu_pressed_close = True
        return True

    def _menu_clicked_row(self, event):
        self._update_menu_hover(event)
        row = self._menu_hovered_row
        if row is None or row.kind not in {'OPERATOR', 'PROPERTY', 'ENUM_ITEM'}:
            return None
        if row.enabled:
            return row
        status = getattr(row.status_info, 'status', ElementStatus.VALID)
        return row if status.is_error else None

    def _menu_property_arrow_direction(self, row, event) -> int:
        return number_part_direction(
            self._menu_number_part(row, self._menu_mouse(event)),
        )

    def _menu_mark_context_changed(self) -> None:
        self._menu_layout_dirty = True
        state = getattr(self, '_menu_tooltip_state', None)
        if state is not None and state.target is not None:
            from ..element.element_tooltip import build_runtime_tooltip

            state.tooltip = build_runtime_tooltip(
                state.target,
                preview_read_only=bool(getattr(self, 'preview_read_only', False)),
            )
        self._tag_menu_redraw()
