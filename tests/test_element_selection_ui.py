from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
ELEMENT_DRAW_PATH = ROOT / 'element' / 'element_draw.py'
UI_INIT_PATH = ROOT / 'ui' / '__init__.py'
UI_LIST_PATH = ROOT / 'ui' / 'ui_list.py'


def _dotted_name(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return '.'.join(reversed(parts))


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class ElementSelectionUiTests(unittest.TestCase):
    def test_element_row_uses_one_way_selection_operator(self):
        tree = ast.parse(ELEMENT_DRAW_PATH.read_text(encoding='utf-8'))
        owner = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'ElementDraw'
        )
        draw = next(
            node for node in owner.body
            if isinstance(node, ast.FunctionDef) and node.name == 'draw_item_right'
        )
        calls = [node for node in ast.walk(draw) if isinstance(node, ast.Call)]

        self.assertFalse(any(
            _dotted_name(call.func).endswith('.prop')
            and len(call.args) >= 2
            and _literal_string(call.args[1]) == 'radio'
            for call in calls
        ))
        self.assertTrue(any(
            _dotted_name(call.func).endswith('.context_pointer_set')
            and call.args
            and _literal_string(call.args[0]) == 'gesture_select_element'
            for call in calls
        ))
        self.assertTrue(any(
            _dotted_name(call.func).endswith('.operator')
            and call.args
            and _dotted_name(call.args[0]) == 'ElementSelect.bl_idname'
            for call in calls
        ))

    def test_selection_operator_is_property_free_and_registered(self):
        tree = ast.parse(UI_LIST_PATH.read_text(encoding='utf-8'))
        operator = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'ElementSelect'
        )
        self.assertEqual(
            [_dotted_name(base) for base in operator.bases],
            ['bpy.types.Operator'],
        )
        self.assertFalse(any(
            isinstance(node, ast.AnnAssign) for node in operator.body
        ))
        execute = next(
            node for node in operator.body
            if isinstance(node, ast.FunctionDef) and node.name == 'execute'
        )
        self.assertTrue(any(
            isinstance(node, ast.Call)
            and _dotted_name(node.func) == 'select_element'
            for node in ast.walk(execute)
        ))

        registry_tree = ast.parse(UI_INIT_PATH.read_text(encoding='utf-8'))
        registry = next(
            node.value for node in registry_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == 'operator_list'
                for target in node.targets
            )
        )
        self.assertIn(
            'ui_list.ElementSelect',
            {_dotted_name(item) for item in registry.elts},
        )


if __name__ == '__main__':
    unittest.main()
