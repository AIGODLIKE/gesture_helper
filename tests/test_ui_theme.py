from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest


UTILS_PATH = Path(__file__).parents[1] / "utils"
PACKAGE = "_gesture_ui_theme_test"


def _load_theme_module():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(UTILS_PATH)]
    sys.modules[PACKAGE] = package
    name = f"{PACKAGE}.ui_theme"
    spec = importlib.util.spec_from_file_location(name, UTILS_PATH / "ui_theme.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ui_theme = _load_theme_module()


class UiThemeTests(unittest.TestCase):
    def test_all_selectable_presets_are_complete_rgba_palettes(self):
        item_ids = {item[0] for item in ui_theme.THEME_PRESET_ITEMS}
        self.assertEqual(
            set(ui_theme.THEME_PRESETS),
            item_ids - {"CUSTOM"},
        )
        self.assertGreaterEqual(len(ui_theme.THEME_PRESETS), 5)
        expected_fields = set(ui_theme.THEME_COLOR_FIELDS)
        for identifier, palette in ui_theme.THEME_PRESETS.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(set(palette), expected_fields)
                for color in palette.values():
                    self.assertEqual(len(color), 4)
                    self.assertTrue(all(0.0 <= component <= 1.0 for component in color))

    def test_applying_preset_replaces_every_theme_color(self):
        target = SimpleNamespace()

        self.assertTrue(ui_theme.apply_theme_preset(target, "MINIMAL_DARK"))
        for name in ui_theme.THEME_COLOR_FIELDS:
            self.assertEqual(
                tuple(getattr(target, name)),
                ui_theme.THEME_PRESETS["MINIMAL_DARK"][name],
            )
        self.assertFalse(ui_theme.apply_theme_preset(target, "CUSTOM"))

    def test_interaction_colors_keep_normal_hover_and_pressed_distinct(self):
        draw = SimpleNamespace(
            interaction_hover_color=(0.2, 0.6, 0.9, 1.0),
            interaction_pressed_color=(0.02, 0.12, 0.3, 1.0),
        )
        base = (0.1, 0.1, 0.1, 0.73)

        normal = ui_theme.interaction_color(draw, base)
        hovered = ui_theme.interaction_color(draw, base, hovered=True)
        pressed = ui_theme.interaction_color(
            draw,
            base,
            hovered=True,
            pressed=True,
        )

        self.assertEqual(normal, base)
        self.assertEqual(normal[3], hovered[3])
        self.assertEqual(normal[3], pressed[3])
        self.assertEqual(len({normal, hovered, pressed}), 3)

    def test_each_preset_keeps_text_legible_and_pointer_states_distinct(self):
        def luminance(color):
            return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]

        for identifier, palette in ui_theme.THEME_PRESETS.items():
            with self.subTest(identifier=identifier):
                draw = SimpleNamespace(**palette)
                normal = palette["background_operator_color"]
                hovered = ui_theme.interaction_color(draw, normal, hovered=True)
                pressed = ui_theme.interaction_color(draw, normal, pressed=True)
                self.assertEqual(len({normal, hovered, pressed}), 3)
                self.assertGreater(
                    abs(
                        luminance(palette["text_default_color"])
                        - luminance(normal)
                    ),
                    0.25,
                )


if __name__ == "__main__":
    unittest.main()
