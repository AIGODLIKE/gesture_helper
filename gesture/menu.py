"""Persistent menu runtime shared by the menu operator and unregister cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import bpy

from ..utils.blf_text import measure_text
from ..utils.color import color_to_srgb
from ..utils.gesture_items import get_gesture_extension_items, poll_context_fingerprint
from ..utils.public_gpu import PublicGpu, gpu_draw_begin, gpu_draw_end
from ..utils.region_mouse import find_window_region, mouse_in_window_region
from ..element.element_status import ElementStatus, get_element_status_info


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
    shadow: tuple
    error: tuple
    warning: tuple


@dataclass
class MenuRow:
    element: Any
    label: str
    kind: str
    enabled: bool = True
    status_info: Any = None
    rect: tuple[float, float, float, float] | None = None


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

    @classmethod
    def _context_instance(cls):
        area = getattr(bpy.context, 'area', None)
        if area is None:
            return None
        try:
            return cls._active_by_area.get(area.as_pointer())
        except ReferenceError:
            return None

    @classmethod
    def _draw_callback(cls):
        instance = cls._context_instance()
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
                instance._menu_close_requested = True
                instance._tag_menu_redraw()
            except (AttributeError, ReferenceError, RuntimeError):
                ...
        cls._active_by_window.clear()
        cls._active_by_area.clear()
        cls._remove_draw_handlers()
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
        space = context.space_data
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
        from ..utils.session_state import SessionState

        SessionState.gesture_menu_active = True
        self._tag_menu_redraw()
        return True

    def _unregister_menu_runtime(self) -> None:
        window_key = getattr(self, '_menu_window_key', None)
        area_key = getattr(self, '_menu_area_key', None)
        if window_key is not None and self._active_by_window.get(window_key) is self:
            self._active_by_window.pop(window_key, None)
        if area_key is not None and self._active_by_area.get(area_key) is self:
            self._active_by_area.pop(area_key, None)
        if not self._active_by_window:
            self._remove_draw_handlers()
        try:
            from ..utils.session_state import SessionState

            SessionState.gesture_menu_active = bool(self._active_by_window)
        except ImportError:
            ...
        self._tag_menu_redraw()

    def _tag_menu_redraw(self) -> None:
        area = getattr(self, '_menu_area', None)
        try:
            if area is not None:
                area.tag_redraw()
        except ReferenceError:
            ...

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
        return MenuColors(
            background=background,
            header=header,
            hover=hover,
            text=text,
            text_hover=text_hover,
            text_disabled=(*text[:3], 0.42),
            outline=outline,
            separator=(*outline[:3], 0.7),
            shadow=(0.0, 0.0, 0.0, 0.28),
            error=(0.72, 0.08, 0.06, 0.9),
            warning=(0.92, 0.48, 0.06, 0.95),
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
            return MenuRow(
                element,
                element.display_property_text,
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

    def _layout_key(self):
        from ..utils.public_cache import PublicCache

        gesture = self.operator_gesture
        try:
            gesture_key = gesture.as_pointer() if gesture is not None else 0
        except (AttributeError, ReferenceError):
            gesture_key = 0
        return (
            gesture_key,
            PublicCache.__structure_generation__,
            PublicCache.__derived_generation__,
            poll_context_fingerprint(),
            self._menu_style(),
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
        gesture = self.operator_gesture
        area = getattr(self, '_menu_area', None)
        region = find_window_region(area)
        if gesture is None or region is None:
            self._menu_panels = []
            return

        metrics = self._metrics()
        root = MenuPanel(0, self._make_rows(gesture.element), title=gesture.name_translate)
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
        self._menu_panels = panels

    def _draw_panel_background(self, panel, metrics, colors) -> None:
        x1, y1, x2, y2 = panel.rect
        width = x2 - x1
        height = y2 - y1
        center = (x1 + width * 0.5, y1 + height * 0.5)
        style = self._menu_style()
        if style == 'PANEL':
            self.draw_rounded_rectangle_area(
                (center[0] + 3.0 * metrics.scale, center[1] - 3.0 * metrics.scale),
                color=colors.shadow,
                radius=metrics.radius,
                width=width,
                height=height,
            )
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
            inset = height * 0.34
            self.draw_2d_line(
                ((cx1 + inset, cy1 + inset), (cx2 - inset, cy2 - inset)),
                color=colors.text,
                line_width=max(1.0, 1.2 * metrics.scale),
            )
            self.draw_2d_line(
                ((cx1 + inset, cy2 - inset), (cx2 - inset, cy1 + inset)),
                color=colors.text,
                line_width=max(1.0, 1.2 * metrics.scale),
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

        hovered = row is self._menu_hovered_row
        if hovered and row.enabled:
            inset = 2.0 * metrics.scale
            self.draw_rounded_rectangle_area(
                (x1 + width * 0.5, y1 + height * 0.5),
                color=colors.hover,
                radius=max(1.0, metrics.radius - inset),
                width=max(1.0, width - inset * 2.0),
                height=max(1.0, height - inset),
            )
        status = getattr(row.status_info, 'status', ElementStatus.VALID)
        if status is not ElementStatus.VALID:
            marker_color = colors.error if status.is_error else colors.warning
            marker_w = max(2.0, 2.0 * metrics.scale)
            self.draw_rectangle(
                x1 + 2.0 * metrics.scale,
                y1 + 2.0,
                marker_w,
                height - 4.0,
                marker_color,
            )

        text_color = colors.text_hover if hovered and row.enabled else (
            colors.text if row.enabled else colors.text_disabled
        )
        cursor_x = x1 + metrics.pad_x
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
        badge = getattr(row.status_info, 'badge', '') if row.status_info is not None else ''
        if row.kind == 'CHILD':
            right_reserve += metrics.row_height * 0.65
        if badge:
            badge_size = metrics.font_size * 0.72
            badge_w, _line = measure_text(badge, badge_size)
            badge_color = colors.error if status.is_error else colors.warning
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
        self._ensure_layout()
        if not self._menu_panels:
            return
        metrics = self._metrics()
        colors = self._colors()
        gpu_draw_begin()
        try:
            for panel in self._menu_panels:
                self._draw_panel_background(panel, metrics, colors)
                self._draw_header(panel, metrics, colors)
                for row in panel.rows:
                    self._draw_row(row, metrics, colors)
        finally:
            gpu_draw_end()
        self._menu_draw_count += 1

    def _menu_mouse(self, event):
        return mouse_in_window_region(event, getattr(self, '_menu_area', None))

    def _menu_contains(self, point) -> bool:
        return any(_point_in_rect(point, panel.rect) for panel in self._menu_panels)

    def _update_menu_hover(self, event) -> bool:
        self._ensure_layout()
        point = self._menu_mouse(event)
        old_row = self._menu_hovered_row
        hovered = None
        hovered_panel = None
        for panel in reversed(self._menu_panels):
            for row in panel.rows:
                if _point_in_rect(point, row.rect):
                    hovered = row
                    hovered_panel = panel
                    break
            if hovered is not None:
                break

        self._menu_hovered_row = hovered
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
        return old_row is not hovered or path_changed

    def _menu_close_hit(self, event) -> bool:
        if not self._menu_panels:
            return False
        return _point_in_rect(self._menu_mouse(event), self._menu_panels[0].close_rect)

    def _menu_clicked_row(self, event):
        self._update_menu_hover(event)
        row = self._menu_hovered_row
        if row is None or not row.enabled or row.kind not in {'OPERATOR', 'PROPERTY'}:
            return None
        return row

    def _menu_mark_context_changed(self) -> None:
        self._menu_layout_dirty = True
        self._tag_menu_redraw()
