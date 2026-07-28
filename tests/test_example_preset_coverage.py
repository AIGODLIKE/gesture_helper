from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
PRESET_DIR = ROOT / "src" / "preset"


def _assignment(path: Path, name: str) -> ast.AST:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return value
    raise AssertionError(f"Could not find assignment {name!r} in {path}")


def _literal(path: Path, name: str):
    return ast.literal_eval(_assignment(path, name))


def _enum_ids(value) -> set[str]:
    return {str(item[0]) for item in value}


def _items_node(path: Path, field: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != field:
            continue
        # Blender RNA declarations use ``field: bpy.props.EnumProperty(...)``;
        # the call lives in the annotation rather than an assignment value.
        call = node.value if node.value is not None else node.annotation
        if not isinstance(call, ast.Call):
            continue
        for keyword in call.keywords:
            if keyword.arg == "items":
                return keyword.value
    raise AssertionError(f"Could not find EnumProperty items for {field!r}")


def _property_default(path: Path, field: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != field:
            continue
        call = node.value if node.value is not None else node.annotation
        if not isinstance(call, ast.Call):
            continue
        for keyword in call.keywords:
            if keyword.arg == "default":
                return ast.literal_eval(keyword.value)
    raise AssertionError(f"Could not find EnumProperty default for {field!r}")


def _resolve_items(path: Path, node: ast.AST):
    if isinstance(node, ast.Name):
        return _resolve_items(path, _assignment(path, node.id))
    if isinstance(node, ast.Starred):
        return _resolve_items(path, node.value)
    if isinstance(node, ast.Subscript):
        values = _resolve_items(path, node.value)
        index = node.slice
        if isinstance(index, ast.Slice):
            def bound(value):
                return None if value is None else ast.literal_eval(value)

            return values[slice(bound(index.lower), bound(index.upper), bound(index.step))]
        return [values[ast.literal_eval(index)]]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = []
        for item in node.elts:
            if isinstance(item, (ast.Name, ast.Starred, ast.Subscript)):
                values.extend(_resolve_items(path, item))
            else:
                values.append(ast.literal_eval(item))
        return values
    return [ast.literal_eval(node)]


def _element_values(node: dict):
    yield node
    children = node.get("element")
    if isinstance(children, dict):
        for child in children.values():
            if isinstance(child, dict):
                yield from _element_values(child)


def _example_text_values(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"name", "description"} and isinstance(value, str) and value:
                yield value
            yield from _example_text_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from _example_text_values(value)


def _radial_root_directions(elements: dict):
    """Yield real radial slots, flattening only conditional structure wrappers."""
    for element in elements.values():
        if not isinstance(element, dict):
            continue
        if element.get("element_type") == "SELECTED_STRUCTURE":
            children = element.get("element")
            if isinstance(children, dict):
                yield from _radial_root_directions(children)
            continue
        direction = element.get("direction")
        if direction is not None:
            yield str(direction)


def _class_literal(path: Path, class_name: str, field: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for child in node.body:
            if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                continue
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if any(isinstance(target, ast.Name) and target.id == field for target in targets):
                return ast.literal_eval(child.value)
    raise AssertionError(f"Could not find {class_name}.{field} in {path}")


def _property_action_operator_ids(quick_add_path: Path, modal_mouse_path: Path) -> set[str]:
    """Extract every operator produced by the property quick-add implementation."""
    modal_id = _class_literal(modal_mouse_path, "ModalMouseOperator", "bl_idname")
    result = set()
    tree = ast.parse(quick_add_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "_set_context_operator":
            continue
        if len(node.args) < 2:
            continue
        operator_node = node.args[1]
        if isinstance(operator_node, ast.Constant) and isinstance(operator_node.value, str):
            result.add(operator_node.value)
        elif (
            isinstance(operator_node, ast.Attribute)
            and isinstance(operator_node.value, ast.Name)
            and operator_node.value.id == "ModalMouseOperator"
            and operator_node.attr == "bl_idname"
        ):
            result.add(modal_id)
        else:
            raise AssertionError(
                f"Unsupported property action operator expression: {ast.dump(operator_node)}"
            )
    if not result:
        raise AssertionError(f"No property action operators found in {quick_add_path}")
    return result


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


class ExamplePresetCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example_files = sorted(PRESET_DIR.glob("Example *.json"))
        if not cls.example_files:
            raise AssertionError("No bundled example presets found")

        cls.data = []
        for path in cls.example_files:
            with path.open(encoding="utf-8") as handle:
                cls.data.append((path, json.load(handle, object_pairs_hook=_reject_duplicate_keys)))

        enum_path = ROOT / "utils" / "enum.py"
        gesture_path = ROOT / "gesture" / "gesture_property.py"
        element_path = ROOT / "element" / "element_property.py"
        modal_path = ROOT / "element" / "element_modal_operator.py"
        modal_mouse_path = ROOT / "ops" / "modal_mouse.py"
        quick_add_path = ROOT / "ops" / "quick_add" / "create_element_property.py"
        preset_registry_path = ROOT / "utils" / "preset.py"

        cls.expected_gesture_types = _enum_ids(_literal(gesture_path, "GESTURE_TYPE_ITEMS"))
        cls.expected_menu_styles = _enum_ids(_literal(gesture_path, "MENU_STYLE_ITEMS"))
        cls.expected_radial_root_directions = _enum_ids(
            _literal(enum_path, "ENUM_GESTURE_DIRECTION")
        )
        cls.expected_element_types = _enum_ids(_literal(enum_path, "ENUM_ELEMENT_TYPE"))
        cls.expected_selected_types = {
            value.upper() for value in _literal(enum_path, "SELECT_STRUCTURE_ELEMENT")
        }
        cls.expected_operator_types = _enum_ids(_literal(enum_path, "ENUM_OPERATOR_TYPE"))
        operator_contexts = [str(value) for value in _literal(enum_path, "OPERATOR_CONTEXT_ELEMENT")]
        cls.expected_operator_contexts = set(operator_contexts)
        cls.default_operator_context = operator_contexts[0]
        cls.expected_layout_alignments = _enum_ids(
            _resolve_items(element_path, _items_node(element_path, "layout_alignment"))
        )
        cls.default_layout_alignment = _property_default(element_path, "layout_alignment")
        cls.expected_property_drag_modes = _enum_ids(
            _resolve_items(enum_path, _items_node(element_path, "property_drag_mode"))
        )
        cls.default_property_drag_mode = _property_default(element_path, "property_drag_mode")
        cls.expected_number_modes = {
            "ADD",
            "SUBTRACT",
            *_enum_ids(_literal(enum_path, "ENUM_NUMBER_VALUE_CHANGE_MODE")),
        }
        cls.expected_bool_modes = _enum_ids(_literal(enum_path, "ENUM_BOOL_VALUE_CHANGE_MODE"))
        cls.expected_enum_modes = {
            str(item[0]) for item in _resolve_items(modal_path, _items_node(modal_path, "enum_value_mode"))
        }
        cls.modal_mouse_operator_id = _class_literal(
            modal_mouse_path, "ModalMouseOperator", "bl_idname"
        )
        cls.expected_property_action_ids = _property_action_operator_ids(
            quick_add_path, modal_mouse_path
        )
        cls.expected_modal_mouse_modes = _enum_ids(
            _resolve_items(enum_path, _items_node(modal_mouse_path, "value_mode"))
        )
        registry_node = _assignment(preset_registry_path, "DEBUG_ONLY_PRESET_NAMES")
        if not (
            isinstance(registry_node, ast.Call)
            and isinstance(registry_node.func, ast.Name)
            and registry_node.func.id == "frozenset"
            and len(registry_node.args) == 1
        ):
            raise AssertionError("DEBUG_ONLY_PRESET_NAMES must be a literal frozenset")
        cls.debug_only_preset_names = set(ast.literal_eval(registry_node.args[0]))

        cls.observed_gesture_types = set()
        cls.observed_menu_styles = set()
        cls.observed_radial_root_directions = set()
        cls.observed_element_types = set()
        cls.observed_selected_types = set()
        cls.observed_operator_types = set()
        cls.observed_operator_contexts = set()
        cls.observed_layout_alignments = set()
        cls.observed_layout_align_modes = set()
        cls.observed_property_drag_modes = set()
        cls.observed_property_drag_invert_modes = set()
        cls.observed_property_show_value_modes = set()
        cls.observed_property_bool_icon_modes = set()
        cls.observed_number_modes = set()
        cls.observed_bool_modes = set()
        cls.observed_enum_modes = set()
        cls.observed_property_action_ids = set()
        cls.observed_modal_mouse_modes = set()

        for path, preset in cls.data:
            gestures = preset.get("gesture")
            if not isinstance(gestures, dict):
                raise AssertionError(f"{path.name} has no gesture object")
            for gesture in gestures.values():
                gesture_type = gesture.get("gesture_type", "RADIAL")
                cls.observed_gesture_types.add(gesture_type)
                if gesture_type == "MENU":
                    cls.observed_menu_styles.add(gesture.get("menu_style", "PANEL"))
                elements = gesture.get("element") or {}
                if gesture_type == "RADIAL":
                    cls.observed_radial_root_directions.update(
                        _radial_root_directions(elements)
                    )
                for root in elements.values():
                    for element in _element_values(root):
                        element_type = element.get("element_type")
                        if element_type is None:
                            continue
                        cls.observed_element_types.add(element_type)
                        if element_type == "SELECTED_STRUCTURE":
                            cls.observed_selected_types.add(element.get("selected_type"))
                        if element_type in {"ROW", "COLUMN", "BOX"}:
                            cls.observed_layout_alignments.add(
                                element.get("layout_alignment", cls.default_layout_alignment)
                            )
                            cls.observed_layout_align_modes.add(
                                element.get("layout_align", True)
                            )
                        if element_type == "PROPERTY":
                            cls.observed_property_drag_modes.add(
                                element.get("property_drag_mode", cls.default_property_drag_mode)
                            )
                            cls.observed_property_drag_invert_modes.add(
                                element.get("property_drag_invert", False)
                            )
                            cls.observed_property_show_value_modes.add(
                                element.get("property_show_value", True)
                            )
                            cls.observed_property_bool_icon_modes.add(
                                element.get("property_bool_icons_enabled", False)
                            )
                        if element_type == "OPERATOR":
                            cls.observed_operator_types.add(element.get("operator_type", "OPERATOR"))
                            cls.observed_operator_contexts.add(
                                element.get("operator_context", cls.default_operator_context)
                            )
                            raw_properties = element.get("operator_properties", "{}")
                            if not isinstance(raw_properties, str):
                                raise AssertionError(
                                    f"{path.name}: {element.get('name')!r} operator_properties "
                                    "must be text"
                                )
                            try:
                                operator_properties = ast.literal_eval(raw_properties)
                            except (SyntaxError, ValueError) as exc:
                                raise AssertionError(
                                    f"{path.name}: {element.get('name')!r} has invalid "
                                    f"operator_properties: {exc}"
                                ) from exc
                            if not isinstance(operator_properties, dict):
                                raise AssertionError(
                                    f"{path.name}: {element.get('name')!r} operator_properties "
                                    "must evaluate to a dict"
                                )
                            operator_id = element.get("operator_bl_idname")
                            if operator_id in cls.expected_property_action_ids:
                                cls.observed_property_action_ids.add(operator_id)
                            if operator_id == cls.modal_mouse_operator_id:
                                mode = operator_properties.get("value_mode")
                                if mode is not None:
                                    cls.observed_modal_mouse_modes.add(mode)
                            for event in (element.get("modal_events") or {}).values():
                                if "number_value_mode" in event:
                                    cls.observed_number_modes.add(event["number_value_mode"])
                                if "bool_value_mode" in event:
                                    cls.observed_bool_modes.add(event["bool_value_mode"])
                                if "enum_value_mode" in event:
                                    cls.observed_enum_modes.add(event["enum_value_mode"])

    def test_every_example_is_json_with_a_valid_shortcut_shape(self):
        for path, preset in self.data:
            self.assertIsInstance(preset.get("gesture"), dict, path.name)
            for gesture in preset["gesture"].values():
                self.assertFalse(gesture.get("enabled", False), f"{path.name} must stay opt-in")
                key_data = json.loads(gesture.get("key_string", "{}"))
                self.assertIsInstance(key_data, dict, path.name)
                self.assertEqual(key_data.get("type"), "RIGHTMOUSE", path.name)
                self.assertEqual(key_data.get("value"), "PRESS", path.name)
                self.assertFalse(key_data.get("any"), path.name)
                for modifier in ("shift", "ctrl", "alt", "oskey"):
                    self.assertFalse(key_data.get(modifier), path.name)
                self.assertEqual(key_data.get("key_modifier"), "NONE", path.name)
                self.assertIsInstance(json.loads(gesture.get("keymaps_string", "[]")), list)

    def test_every_example_is_registered_as_debug_only(self):
        self.assertEqual(
            {path.stem for path in self.example_files},
            self.debug_only_preset_names,
        )

    def test_every_source_json_rejects_duplicate_keys(self):
        for path in sorted((ROOT / "src").rglob("*.json")):
            with path.open(encoding="utf-8") as handle:
                json.load(handle, object_pairs_hook=_reject_duplicate_keys)

    def test_mx_gizmo_toggle_uses_a_property_element(self):
        path = PRESET_DIR / "MX Preset.json"
        with path.open(encoding="utf-8") as handle:
            preset = json.load(handle, object_pairs_hook=_reject_duplicate_keys)

        matches = [
            element
            for gesture in preset["gesture"].values()
            for root in gesture.get("element", {}).values()
            for element in _element_values(root)
            if (
                element.get("name") == "Show Gizmo"
                and element.get("property_data_path") == "space_data.show_gizmo"
            )
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].get("element_type"), "PROPERTY")
        self.assertNotIn("operator_bl_idname", matches[0])

    def test_gesture_and_menu_types_are_all_demonstrated(self):
        self.assertEqual(self.observed_gesture_types, self.expected_gesture_types)
        self.assertEqual(self.observed_menu_styles, self.expected_menu_styles)

    def test_every_radial_root_direction_is_demonstrated(self):
        self.assertEqual(
            self.observed_radial_root_directions,
            self.expected_radial_root_directions,
        )

    def test_element_and_operator_types_are_all_demonstrated(self):
        self.assertEqual(self.observed_element_types, self.expected_element_types)
        self.assertEqual(self.observed_selected_types, self.expected_selected_types)
        self.assertEqual(self.observed_operator_types, self.expected_operator_types)

    def test_every_operator_context_is_demonstrated(self):
        self.assertEqual(self.observed_operator_contexts, self.expected_operator_contexts)

    def test_layout_and_property_drag_modes_are_all_demonstrated(self):
        self.assertEqual(self.observed_layout_alignments, self.expected_layout_alignments)
        self.assertEqual(self.observed_property_drag_modes, self.expected_property_drag_modes)
        self.assertEqual(self.observed_layout_align_modes, {False, True})
        self.assertEqual(self.observed_property_drag_invert_modes, {False, True})
        self.assertEqual(self.observed_property_show_value_modes, {False, True})
        self.assertEqual(self.observed_property_bool_icon_modes, {False, True})

    def test_modal_control_modes_are_all_demonstrated(self):
        self.assertEqual(self.observed_number_modes, self.expected_number_modes)
        self.assertEqual(self.observed_bool_modes, self.expected_bool_modes)
        self.assertEqual(self.observed_enum_modes, self.expected_enum_modes)

    def test_every_property_action_and_modal_mouse_mode_is_demonstrated(self):
        self.assertEqual(
            self.observed_property_action_ids,
            self.expected_property_action_ids,
        )
        self.assertEqual(
            self.observed_modal_mouse_modes,
            self.expected_modal_mouse_modes,
        )

    def test_every_example_name_and_description_has_a_chinese_translation(self):
        translation_path = ROOT / "src" / "translate" / "zh_CN" / "preset.json"
        with translation_path.open(encoding="utf-8") as handle:
            translations = json.load(handle, object_pairs_hook=_reject_duplicate_keys)

        missing = {}
        for path, preset in self.data:
            values = {path.stem, *_example_text_values(preset)}
            untranslated = sorted(value for value in values if value not in translations)
            if untranslated:
                missing[path.name] = untranslated
        self.assertFalse(missing, missing)


if __name__ == "__main__":
    unittest.main()
