from __future__ import annotations

import ast
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).parents[1]
UI_SOURCE_ROOTS = ("element", "gesture", "ops", "preferences", "ui")
UI_LAYOUT_METHODS = {"label", "menu", "operator", "popover", "prop", "prop_enum"}


class UILayoutIconTests(unittest.TestCase):
    def test_every_explicit_ui_icon_uses_the_version_safe_helper(self):
        failures = []
        for root_name in UI_SOURCE_ROOTS:
            for path in sorted((REPOSITORY / root_name).rglob("*.py")):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
                for node in ast.walk(tree):
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in UI_LAYOUT_METHODS
                    ):
                        continue
                    for keyword in node.keywords:
                        if keyword.arg != "icon":
                            continue
                        safe = (
                            isinstance(keyword.value, ast.Call)
                            and isinstance(keyword.value.func, ast.Name)
                            and keyword.value.func.id == "ui_icon"
                        )
                        if not safe:
                            failures.append(
                                f"{path.relative_to(REPOSITORY)}:{node.lineno}"
                            )

        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
