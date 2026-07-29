from __future__ import annotations

import ast
from pathlib import Path
import unittest


REPOSITORY = Path(__file__).parents[1]


def _class_node(path: Path, name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"{name} class not found in {path}")


def _method_node(class_node: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} method not found in {class_node.name}")


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


class PreferencesPageTests(unittest.TestCase):
    def test_backups_are_a_dedicated_preferences_page(self):
        preferences = _class_node(
            REPOSITORY / "preferences" / "__init__.py",
            "GesturePreferences",
        )
        show_page = next(
            node
            for node in preferences.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "show_page"
        )
        self.assertIsInstance(show_page.annotation, ast.Call)
        items = next(
            keyword.value
            for keyword in show_page.annotation.keywords
            if keyword.arg == "items"
        )

        self.assertEqual(
            [item[0] for item in ast.literal_eval(items)],
            ["GESTURE", "PROPERTY", "BACKUPS", "STYLE"],
        )

    def test_backup_controls_are_not_drawn_on_the_property_page(self):
        draw = _class_node(
            REPOSITORY / "preferences" / "draw.py",
            "PreferencesDraw",
        )
        property_page = _method_node(draw, "draw_ui_property")
        backups_page = _method_node(draw, "draw_ui_backups")

        self.assertNotIn("draw_backups", _called_attributes(property_page))
        self.assertIn("draw_backups", _called_attributes(backups_page))
        backup_source = ast.unparse(backups_page)
        self.assertIn("ExportPreferences.bl_idname", backup_source)
        self.assertIn("ImportPreferences.bl_idname", backup_source)


if __name__ == "__main__":
    unittest.main()
