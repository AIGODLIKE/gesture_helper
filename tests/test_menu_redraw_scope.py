from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "menu.py"
PACKAGE = "_gesture_menu_redraw_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_menu_module():
    root = _module(PACKAGE)
    root.__path__ = [str(MODULE_PATH.parents[1])]
    for package_name, path in (
            ("gesture", MODULE_PATH.parent),
            ("utils", MODULE_PATH.parents[1] / "utils"),
            ("element", MODULE_PATH.parents[1] / "element"),
    ):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = [str(path)]

    bpy = _module("bpy")
    bpy.context = types.SimpleNamespace()
    bpy.app = _module("bpy.app")
    _module("bpy.app.translations", pgettext_iface=lambda text: text)

    _module(
        f"{PACKAGE}.utils.blf_text",
        measure_text=lambda *_args, **_kwargs: (0.0, 0.0),
    )
    _module(
        f"{PACKAGE}.utils.color",
        color_to_srgb=lambda color: color,
    )
    _module(
        f"{PACKAGE}.utils.gesture_items",
        get_gesture_extension_items=lambda _items: (),
        poll_context_fingerprint=lambda: (),
    )

    class PublicGpu:
        pass

    _module(
        f"{PACKAGE}.utils.public_gpu",
        PublicGpu=PublicGpu,
        gpu_draw_begin=lambda: None,
        gpu_draw_end=lambda: None,
    )
    _module(
        f"{PACKAGE}.element.element_status",
        ElementStatus=types.SimpleNamespace(
            VALID=types.SimpleNamespace(is_error=False),
        ),
        get_element_status_info=lambda _element, **_kwargs: None,
    )

    name = f"{PACKAGE}.gesture.menu"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


menu_module = _load_menu_module()


class FakeRegion:
    def __init__(self, region_type):
        self.type = region_type
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class FakeArea:
    def __init__(self, regions):
        self.regions = regions
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class MenuRedrawScopeTests(unittest.TestCase):
    @staticmethod
    def _metrics():
        return menu_module.MenuMetrics(
            scale=1.0,
            font_size=12.0,
            line_height=14.0,
            row_height=24.0,
            separator_height=8.0,
            header_height=24.0,
            pad_x=10.0,
            gap=6.0,
            radius=4.0,
            min_width=180.0,
            max_width=440.0,
            flyout_gap=5.0,
            border_width=1.0,
        )

    @staticmethod
    def _colors():
        return menu_module.MenuColors(
            background=(0.08, 0.08, 0.08, 1.0),
            header=(0.1, 0.1, 0.1, 1.0),
            hover=(0.1, 0.3, 0.6, 1.0),
            text=(0.8, 0.8, 0.8, 1.0),
            text_hover=(1.0, 1.0, 1.0, 1.0),
            text_disabled=(0.4, 0.4, 0.4, 1.0),
            outline=(0.2, 0.2, 0.2, 1.0),
            separator=(0.2, 0.2, 0.2, 1.0),
            error=(0.72, 0.08, 0.06, 0.9),
            warning=(0.92, 0.48, 0.06, 0.95),
            row=(0.12, 0.12, 0.12, 0.96),
            pressed=(0.04, 0.16, 0.38, 1.0),
        )

    def test_error_row_uses_red_background_and_white_text(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        status = types.SimpleNamespace(is_error=True)
        row = menu_module.MenuRow(
            None,
            "Broken",
            "OPERATOR",
            enabled=False,
            status_info=types.SimpleNamespace(status=status, badge="OP"),
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        colors = self._colors()

        runtime._draw_row(row, self._metrics(), colors)

        self.assertEqual(
            runtime.draw_rounded_rectangle_area.call_args.kwargs["color"],
            colors.error,
        )
        self.assertEqual(
            runtime.draw_text.call_args.kwargs["color"],
            colors.text_hover,
        )

    def test_menu_redraw_targets_only_owner_window_region(self):
        ui_region = FakeRegion("UI")
        window_region = FakeRegion("WINDOW")
        area = FakeArea([ui_region, window_region])
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_area = area

        runtime._tag_menu_redraw()

        self.assertEqual(window_region.redraws, 1)
        self.assertEqual(ui_region.redraws, 0)
        self.assertEqual(area.redraws, 0)

    def test_menu_redraw_has_no_whole_area_fallback(self):
        ui_region = FakeRegion("UI")
        area = FakeArea([ui_region])
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_area = area

        runtime._tag_menu_redraw()

        self.assertEqual(ui_region.redraws, 0)
        self.assertEqual(area.redraws, 0)

    def test_menu_draw_callback_ignores_conflicting_gpu_context_lookup(self):
        class ConflictingGpuBase:
            @staticmethod
            def _context_instance():
                return None

        class PreviewLike(ConflictingGpuBase, menu_module.GestureMenuRuntime):
            _active_by_area = {}

        area = types.SimpleNamespace(as_pointer=lambda: 17)
        runtime = types.SimpleNamespace(
            _menu_close_requested=False,
            _menu_last_draw_error='',
            _draw_menu=Mock(),
        )
        PreviewLike._active_by_area[17] = runtime
        previous_area = getattr(menu_module.bpy.context, 'area', None)
        try:
            menu_module.bpy.context.area = area
            PreviewLike._draw_callback()
        finally:
            menu_module.bpy.context.area = previous_area

        runtime._draw_menu.assert_called_once_with()
        self.assertEqual(runtime._menu_last_draw_error, '')

    def test_menu_transition_reveal_is_bidirectional(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_opened_at = 10.0
        runtime._menu_closing_at = 0.0

        self.assertEqual(runtime._menu_animation_reveal(now=10.0), 0.0)
        self.assertAlmostEqual(
            runtime._menu_animation_reveal(
                now=10.0 + menu_module.MENU_TRANSITION_SECONDS * 0.5,
            ),
            0.5,
        )
        self.assertEqual(
            runtime._menu_animation_reveal(
                now=10.0 + menu_module.MENU_TRANSITION_SECONDS,
            ),
            1.0,
        )

        runtime._menu_closing_at = 20.0
        runtime._menu_close_start_reveal = 1.0
        self.assertEqual(runtime._menu_animation_reveal(now=20.0), 1.0)
        self.assertAlmostEqual(
            runtime._menu_animation_reveal(
                now=20.0 + menu_module.MENU_TRANSITION_SECONDS * 0.5,
            ),
            0.5,
        )
        self.assertEqual(
            runtime._menu_animation_reveal(
                now=20.0 + menu_module.MENU_TRANSITION_SECONDS,
            ),
            0.0,
        )

    def test_close_started_after_open_preserves_full_reveal(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_opened_at = 10.0
        runtime._menu_closing_at = 0.0
        runtime._menu_close_requested = False
        runtime._menu_close_start_reveal = 1.0
        runtime._menu_tooltip_state = None
        runtime._menu_hovered_row = object()
        runtime._menu_pressed_close = True
        runtime._menu_drag_mouse = (1.0, 2.0)
        runtime._menu_drag_button = "LEFTMOUSE"
        runtime._schedule_menu_animation = Mock()
        runtime._tag_menu_redraw = Mock()

        with patch.object(menu_module.time, "monotonic", return_value=20.0):
            self.assertTrue(runtime._begin_menu_close())

        self.assertEqual(runtime._menu_close_start_reveal, 1.0)
        self.assertEqual(runtime._menu_closing_at, 20.0)
        self.assertIsNone(runtime._menu_hovered_row)
        self.assertTrue(runtime._menu_pressed_close)
        self.assertIsNone(runtime._menu_drag_mouse)
        runtime._schedule_menu_animation.assert_called_once_with()
        runtime._tag_menu_redraw.assert_called_once_with()

    def test_header_drag_moves_centered_menu_from_its_drawn_position(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_panels = [menu_module.MenuPanel(
            depth=0,
            rows=[],
            rect=(20.0, 30.0, 120.0, 90.0),
            header_rect=(20.0, 70.0, 120.0, 90.0),
            close_rect=(100.0, 70.0, 120.0, 90.0),
        )]
        runtime._menu_centered = True
        runtime._menu_anchor = (0.0, 0.0)
        runtime._menu_drag_mouse = None
        runtime._menu_drag_button = None
        runtime._menu_layout_dirty = False
        runtime._menu_mouse = lambda event: event.point
        runtime._ensure_layout = lambda **_kwargs: None
        runtime._sync_menu_tooltip = lambda _row: None
        runtime._tag_menu_redraw = Mock()

        press = types.SimpleNamespace(point=(40.0, 80.0))
        move = types.SimpleNamespace(type="MOUSEMOVE", point=(55.0, 72.0))
        self.assertTrue(runtime._menu_header_hit(press))
        self.assertTrue(runtime._start_menu_drag(press, button="LEFTMOUSE"))
        self.assertFalse(runtime._menu_centered)
        self.assertEqual(runtime._menu_anchor, (20.0, 90.0))
        self.assertTrue(runtime._move_menu_drag(move))
        self.assertEqual(runtime._menu_anchor, (35.0, 82.0))
        self.assertTrue(runtime._menu_layout_dirty)
        runtime._tag_menu_redraw.assert_called_once_with()
        self.assertTrue(runtime._finish_menu_drag(button="LEFTMOUSE"))

    def test_boolean_property_uses_optional_checkbox_and_numeric_property_draws_arrows(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime._menu_current_reveal = 1.0
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime.draw_2d_line = Mock()
        runtime.draw_image = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        colors = self._colors()

        boolean_row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="BOOLEAN",
                display_property_value=True,
                display_property_fraction=None,
                is_draw_icon=False,
                property_bool_icons_enabled=False,
            ),
            "Enabled",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        runtime._draw_row(boolean_row, self._metrics(), colors)
        self.assertEqual(runtime.draw_rounded_rectangle_area.call_count, 1)
        self.assertEqual(
            runtime.draw_rounded_rectangle_area.call_args.kwargs["color"],
            colors.background,
        )
        runtime.draw_image.assert_not_called()
        self.assertIsNone(boolean_row.decrement_rect)
        self.assertIsNone(boolean_row.increment_rect)

        runtime.draw_2d_line.reset_mock()
        runtime.draw_rounded_rectangle_area.reset_mock()
        runtime.draw_rectangle.reset_mock()
        numeric_row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="FLOAT",
                display_property_value=0.2,
                display_property_fraction=0.2,
                display_property_is_editable=True,
                is_draw_icon=False,
            ),
            "Amount  0.20",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        with patch.object(menu_module, "show_number_arrows", return_value=True):
            runtime._draw_row(numeric_row, self._metrics(), colors)
        self.assertIsNotNone(numeric_row.decrement_rect)
        self.assertIsNotNone(numeric_row.value_rect)
        self.assertIsNotNone(numeric_row.increment_rect)
        self.assertEqual(numeric_row.decrement_rect[0], numeric_row.rect[0])
        self.assertEqual(numeric_row.decrement_rect[2], numeric_row.value_rect[0])
        self.assertEqual(numeric_row.value_rect[2], numeric_row.increment_rect[0])
        self.assertEqual(numeric_row.increment_rect[2], numeric_row.rect[2])
        self.assertEqual(runtime.draw_2d_line.call_count, 4)
        self.assertEqual(runtime.draw_rounded_rectangle_area.call_count, 4)
        runtime.draw_rectangle.assert_not_called()

    def test_menu_row_has_distinct_normal_hover_and_pressed_surfaces(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime._menu_pressed_row = None
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        colors = self._colors()
        row = menu_module.MenuRow(
            types.SimpleNamespace(is_draw_icon=False),
            "Action",
            "OPERATOR",
            rect=(0.0, 0.0, 200.0, 24.0),
        )

        runtime._draw_row(row, self._metrics(), colors)
        normal = runtime.draw_rounded_rectangle_area.call_args.kwargs["color"]
        runtime._menu_hovered_row = row
        runtime._draw_row(row, self._metrics(), colors)
        hovered = runtime.draw_rounded_rectangle_area.call_args.kwargs["color"]
        runtime._menu_pressed_row = row
        runtime._draw_row(row, self._metrics(), colors)
        pressed = runtime.draw_rounded_rectangle_area.call_args.kwargs["color"]

        self.assertEqual(normal, colors.background)
        self.assertEqual(hovered, colors.hover)
        self.assertEqual(pressed, colors.pressed)
        self.assertEqual(len({normal, hovered, pressed}), 3)

    def test_menu_rows_fill_their_complete_adjacent_bounds(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime._menu_pressed_row = None
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        row = menu_module.MenuRow(
            types.SimpleNamespace(is_draw_icon=False),
            "Action",
            "OPERATOR",
            rect=(0.0, 24.0, 200.0, 48.0),
        )

        runtime._draw_row(row, self._metrics(), self._colors())

        surface = runtime.draw_rounded_rectangle_area.call_args.kwargs
        self.assertEqual(surface["width"], 200.0)
        self.assertEqual(surface["height"], 24.0)

    def test_menu_rows_keep_only_exposed_panel_corners(self):
        root = menu_module.MenuPanel(
            depth=0,
            rows=[],
            rect=(0.0, 0.0, 200.0, 72.0),
            header_rect=(0.0, 48.0, 200.0, 72.0),
        )
        middle = menu_module.MenuRow(
            None,
            "Middle",
            "OPERATOR",
            rect=(0.0, 24.0, 200.0, 48.0),
        )
        bottom = menu_module.MenuRow(
            None,
            "Bottom",
            "OPERATOR",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        flyout = menu_module.MenuPanel(
            depth=1,
            rows=[],
            rect=(0.0, 0.0, 200.0, 48.0),
        )
        flyout_top = menu_module.MenuRow(
            None,
            "Top",
            "OPERATOR",
            rect=(0.0, 24.0, 200.0, 48.0),
        )

        self.assertEqual(
            menu_module._menu_row_corner_mask(root, middle),
            (False, False, False, False),
        )
        self.assertEqual(
            menu_module._menu_row_corner_mask(root, bottom),
            (False, False, True, True),
        )
        self.assertEqual(
            menu_module._menu_row_corner_mask(flyout, flyout_top),
            (True, True, False, False),
        )

    def test_read_only_menu_preview_keeps_normal_scale(self):
        menu_module.bpy.context.preferences = types.SimpleNamespace(
            view=types.SimpleNamespace(ui_scale=1.0),
        )
        runtime = menu_module.GestureMenuRuntime()
        runtime.preview_read_only = False
        self.assertEqual(runtime._metrics().scale, 1.0)
        runtime.preview_read_only = True
        self.assertEqual(runtime._metrics().scale, 1.0)

    def test_menu_close_button_has_distinct_hover_and_pressed_surfaces(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime.draw_2d_line = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        panel = menu_module.MenuPanel(
            depth=0,
            rows=[],
            title="Menu",
            header_rect=(0.0, 0.0, 200.0, 24.0),
            close_rect=(176.0, 0.0, 200.0, 24.0),
        )
        colors = self._colors()

        runtime._menu_hovered_close = True
        runtime._menu_pressed_close = False
        runtime._draw_header(panel, self._metrics(), colors)
        hover = runtime.draw_rounded_rectangle_area.call_args.kwargs["color"]
        runtime._menu_pressed_close = True
        runtime._draw_header(panel, self._metrics(), colors)
        pressed = runtime.draw_rounded_rectangle_area.call_args.kwargs["color"]

        self.assertEqual(hover, colors.hover)
        self.assertEqual(pressed, colors.pressed)
        self.assertNotEqual(hover, pressed)

    def test_enum_property_opens_blender_style_choices_and_sets_one(self):
        items = (
            types.SimpleNamespace(identifier="SOLID", name="Solid"),
            types.SimpleNamespace(identifier="MATERIAL", name="Material Preview"),
        )
        rna_prop = types.SimpleNamespace(type="ENUM", enum_items=items)
        changes = []
        element = types.SimpleNamespace(
            display_property_type="ENUM",
            display_property_value="SOLID",
            display_property_is_editable=True,
            resolve_property=lambda: (object(), rna_prop),
            set_display_property_value=lambda value: changes.append(value) or True,
        )
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_enum_dropdown = None
        runtime._menu_layout_dirty = False
        runtime._ensure_layout = Mock()
        runtime._tag_menu_redraw = Mock()
        runtime._menu_mark_context_changed = Mock()
        row = menu_module.MenuRow(element, "Shading", "PROPERTY")

        self.assertTrue(runtime._toggle_menu_enum_dropdown(row))
        self.assertIs(runtime._menu_enum_dropdown, element)
        choices = runtime._enum_choice_rows(element)
        self.assertEqual([choice.label for choice in choices], ["Solid", "Material Preview"])
        self.assertTrue(choices[0].enum_active)
        self.assertFalse(choices[1].enum_active)

        self.assertTrue(runtime._set_menu_enum_choice(choices[1]))
        self.assertEqual(changes, ["MATERIAL"])
        self.assertIsNone(runtime._menu_enum_dropdown)
        runtime._menu_mark_context_changed.assert_called_once_with()

    def test_numeric_property_tracks_three_hover_regions_and_press_release(self):
        runtime = menu_module.GestureMenuRuntime()
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="FLOAT",
                display_property_is_editable=True,
            ),
            "Amount  0.20",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        runtime._menu_panels = [menu_module.MenuPanel(0, [row])]
        runtime._menu_open_path = []
        runtime._menu_hovered_row = None
        runtime._menu_hovered_part = None
        runtime._menu_pressed_row = None
        runtime._menu_pressed_part = None
        runtime._ensure_layout = lambda **_kwargs: None
        runtime._metrics = self._metrics
        runtime._menu_mouse = lambda event: event.point
        runtime._sync_menu_tooltip = lambda _element: False

        with patch.object(menu_module, "show_number_arrows", return_value=True):
            for point, expected in (
                ((3.0, 12.0), menu_module.NUMBER_PART_DECREMENT),
                ((100.0, 12.0), menu_module.NUMBER_PART_VALUE),
                ((197.0, 12.0), menu_module.NUMBER_PART_INCREMENT),
            ):
                event = types.SimpleNamespace(point=point)
                self.assertTrue(runtime._update_menu_hover(event))
                self.assertEqual(runtime._menu_hovered_part, expected)

            press = types.SimpleNamespace(point=(197.0, 12.0))
            self.assertTrue(runtime._press_menu_row(row, press))
            self.assertIs(runtime._menu_pressed_row, row)
            self.assertEqual(runtime._menu_pressed_part, menu_module.NUMBER_PART_INCREMENT)
            self.assertTrue(runtime._clear_menu_press())
            self.assertIsNone(runtime._menu_pressed_row)
            self.assertIsNone(runtime._menu_pressed_part)

    def test_numeric_value_hover_fill_is_drawn_beneath_active_text(self):
        runtime = menu_module.GestureMenuRuntime()
        events = []
        runtime._menu_current_reveal = 1.0
        runtime.draw_rounded_rectangle_area = (
            lambda *_args, **_kwargs: events.append("fill")
        )
        runtime.draw_rectangle = lambda *_args, **_kwargs: events.append("accent")
        runtime.draw_text = (
            lambda *_args, **kwargs: events.append(("text", kwargs["color"]))
        )
        runtime.draw_2d_line = lambda *_args, **_kwargs: events.append("arrow")
        runtime.draw_image = lambda *_args, **_kwargs: events.append("image")
        runtime._fit_text = lambda text, _width, _size: text
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="FLOAT",
                display_property_value=0.2,
                display_property_fraction=0.2,
                display_property_is_editable=True,
                is_draw_icon=False,
            ),
            "Amount  0.20",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        runtime._menu_hovered_row = row
        runtime._menu_hovered_part = menu_module.NUMBER_PART_VALUE
        runtime._menu_pressed_row = None
        runtime._menu_pressed_part = None
        colors = self._colors()

        with patch.object(menu_module, "show_number_arrows", return_value=True):
            runtime._draw_row(row, self._metrics(), colors)

        text_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, tuple) and event[0] == "text"
        )
        self.assertGreater(text_index, max(
            index for index, event in enumerate(events) if event == "fill"
        ))
        self.assertEqual(events[text_index][1], colors.text_hover)

    def test_numeric_arrow_hover_does_not_change_value_surface_or_text(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_current_reveal = 1.0
        runtime.draw_rectangle = Mock()
        runtime.draw_2d_line = Mock()
        runtime.draw_image = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="FLOAT",
                display_property_value=0.2,
                display_property_fraction=0.2,
                display_property_is_editable=True,
                is_draw_icon=False,
            ),
            "Amount  0.20",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )
        colors = self._colors()

        def draw(hovered_part):
            runtime._menu_hovered_row = row if hovered_part is not None else None
            runtime._menu_hovered_part = hovered_part
            runtime._menu_pressed_row = None
            runtime._menu_pressed_part = None
            runtime.draw_rounded_rectangle_area = Mock()
            runtime.draw_text = Mock()
            runtime._draw_row(row, self._metrics(), colors)
            fills = [
                call.kwargs["color"]
                for call in runtime.draw_rounded_rectangle_area.call_args_list
            ]
            return fills, runtime.draw_text.call_args.kwargs["color"]

        with patch.object(menu_module, "show_number_arrows", return_value=True):
            normal_fills, normal_text = draw(None)
            arrow_fills, arrow_text = draw(menu_module.NUMBER_PART_DECREMENT)

        self.assertEqual(len(normal_fills), 4)
        self.assertEqual(len(arrow_fills), 4)
        self.assertEqual(arrow_fills[:2], normal_fills[:2])
        self.assertNotEqual(arrow_fills[2], normal_fills[2])
        self.assertEqual(arrow_fills[3], normal_fills[3])
        self.assertEqual(normal_text, colors.text)
        self.assertEqual(arrow_text, colors.text)

    def test_read_only_numeric_property_does_not_advertise_arrow_controls(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime._menu_pressed_row = None
        runtime._menu_current_reveal = 1.0
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime.draw_2d_line = Mock()
        runtime.draw_image = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="FLOAT",
                display_property_value=0.2,
                display_property_fraction=0.2,
                display_property_is_editable=False,
                is_draw_icon=False,
            ),
            "Amount  0.20",
            "PROPERTY",
            enabled=False,
            rect=(0.0, 0.0, 200.0, 24.0),
        )

        with patch.object(menu_module, "show_number_arrows", return_value=True):
            runtime._draw_row(row, self._metrics(), self._colors())

        self.assertIsNone(row.decrement_rect)
        self.assertIsNone(row.value_rect)
        self.assertIsNone(row.increment_rect)
        runtime.draw_2d_line.assert_not_called()

    def test_boolean_property_draws_native_checkbox_when_state_icons_are_enabled(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime.draw_image = Mock()
        texture = object()
        _module(
            f"{PACKAGE}.utils.texture",
            Texture=types.SimpleNamespace(get_texture=lambda icon: texture),
        )
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_value=True,
                property_bool_icons_enabled=True,
            ),
            "Enabled",
            "PROPERTY",
        )

        occupied = runtime._draw_boolean_state_icon(
            row,
            x=10.0,
            y1=0.0,
            height=24.0,
            metrics=self._metrics(),
        )

        self.assertGreater(occupied, 0.0)
        runtime.draw_image.assert_called_once_with((10.0, 5.0), 14.0, 14.0, texture=texture)

    def test_boolean_property_row_does_not_repeat_configured_state_icon(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime._menu_hovered_row = None
        runtime._menu_pressed_row = None
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime.draw_2d_line = Mock()
        runtime.draw_image = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        texture_names = []
        texture = object()

        def get_texture(name):
            texture_names.append(name)
            return texture

        _module(
            f"{PACKAGE}.utils.texture",
            Texture=types.SimpleNamespace(get_texture=get_texture),
        )
        row = menu_module.MenuRow(
            types.SimpleNamespace(
                display_property_type="BOOLEAN",
                display_property_value=True,
                display_property_fraction=None,
                property_bool_icons_enabled=True,
                is_draw_icon=True,
                _gpu_draw_icon_name=lambda: "CHECKBOX_HLT",
            ),
            "Overlays: Visible",
            "PROPERTY",
            rect=(0.0, 0.0, 200.0, 24.0),
        )

        runtime._draw_row(row, self._metrics(), self._colors())

        self.assertEqual(texture_names, ["CHECKBOX_HLT"])
        runtime.draw_image.assert_called_once_with(
            (10.0, 5.0),
            14.0,
            14.0,
            texture=texture,
        )

    def test_header_has_square_lower_corners(self):
        runtime = menu_module.GestureMenuRuntime()
        runtime.draw_rounded_rectangle_area = Mock()
        runtime.draw_rectangle = Mock()
        runtime.draw_text = Mock()
        runtime.draw_2d_line = Mock()
        runtime._fit_text = lambda text, _width, _size: text
        panel = menu_module.MenuPanel(
            depth=0,
            rows=[],
            title="Menu",
            header_rect=(0.0, 20.0, 200.0, 44.0),
        )

        runtime._draw_header(panel, self._metrics(), self._colors())

        runtime.draw_rectangle.assert_called_once_with(0.0, 20.0, 200.0, 4.0, self._colors().header)


if __name__ == "__main__":
    unittest.main()
