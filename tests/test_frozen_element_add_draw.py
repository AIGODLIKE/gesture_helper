from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
DRAW_ELEMENT_PATH = ROOT / "preferences" / "draw_element.py"
DRAW_GESTURE_PATH = ROOT / "preferences" / "draw_gesture.py"
ELEMENT_CURE_PATH = ROOT / "element" / "element_cure.py"
GESTURE_INIT_PATH = ROOT / "gesture" / "__init__.py"
OPS_INIT_PATH = ROOT / "ops" / "__init__.py"
PANEL_PATH = ROOT / "ui" / "panel.py"
PREVIEW_PATH = ROOT / "ops" / "quick_add" / "gesture_preview.py"
PACKAGE = "_gesture_frozen_element_add_test"
_PREF = None


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _get_pref():
    return _PREF


class _RealAdd:
    bl_idname = "wm.gesture_element_add"


class _FrozenAdd:
    bl_idname = "wm.gesture_element_add_frozen"


class _ElementCURE:
    ADD = _RealAdd
    FrozenADD = _FrozenAdd


class _LayoutPresetMenu:
    pass


class _AddElementMenu:
    pass


class _GesturePreview:
    bl_idname = "wm.gesture_preview"


class _GesturePreviewClose:
    bl_idname = "wm.gesture_preview_close"


class _GesturePreviewFrozen:
    bl_idname = "wm.gesture_preview_frozen"


class _PreviewSessionState:
    gesture_preview_active = False
    gesture_preview_scope = ""


def _load_draw_element_module():
    root = _module(PACKAGE)
    root.__path__ = [str(ROOT)]
    for package_name, path in (
            ("preferences", ROOT / "preferences"),
            ("utils", ROOT / "utils"),
            ("element", ROOT / "element"),
            ("ui", ROOT / "ui"),
    ):
        package = _module(f"{PACKAGE}.{package_name}")
        package.__path__ = [str(path)]

    _module(
        f"{PACKAGE}.utils.public",
        get_pref=_get_pref,
        get_debug=lambda: False,
    )
    _module(f"{PACKAGE}.utils.icons", ui_icon=lambda name: name)
    _module(f"{PACKAGE}.utils.public_ui", icon_two=lambda *_args, **_kwargs: "NONE")
    _module(
        f"{PACKAGE}.utils.enum",
        ENUM_SELECTED_TYPE=(
            ("BUTTON", "Button", ""),
            ("SLIDER", "Slider", ""),
        ),
        ENUM_ELEMENT_TYPE=(
            ("SELECTED_STRUCTURE", "Structure", ""),
            ("OPERATOR", "Operator", ""),
            ("DIVIDING_LINE", "Div", ""),
            ("ROW", "Row", ""),
            ("COLUMN", "Column", ""),
            ("BOX", "Box", ""),
            ("LABEL", "Label", ""),
            ("SPLIT", "Split", ""),
        ),
        ENUM_LAYOUT_TYPE=(
            ("ROW", "Row", ""),
            ("COLUMN", "Column", ""),
            ("BOX", "Box", ""),
            ("SPLIT", "Split", ""),
        ),
        ENUM_LAYOUT_ELEMENT_TYPE=(
            ("ROW", "Row", ""),
            ("COLUMN", "Column", ""),
            ("BOX", "Box", ""),
            ("LABEL", "Label", ""),
            ("SPLIT", "Split", ""),
        ),
    )
    sys.modules[f"{PACKAGE}.element"].ElementCURE = _ElementCURE
    _module(
        f"{PACKAGE}.ui.menu",
        GESTURE_MT_add_element_menu=_AddElementMenu,
        GESTURE_MT_layout_preset_menu=_LayoutPresetMenu,
    )

    fake_bpy = types.ModuleType("bpy")
    fake_bpy.types = types.SimpleNamespace(UILayout=object)
    fake_bpy.context = types.SimpleNamespace(
        region=types.SimpleNamespace(width=280),
        area=types.SimpleNamespace(type="VIEW_3D"),
    )
    fake_app = types.ModuleType("bpy.app")
    fake_app.__path__ = []
    fake_translations = types.ModuleType("bpy.app.translations")
    fake_translations.pgettext = lambda value: value

    name = f"{PACKAGE}.preferences.draw_element"
    spec = importlib.util.spec_from_file_location(name, DRAW_ELEMENT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with patch.dict(
            sys.modules,
            {
                "bpy": fake_bpy,
                "bpy.app": fake_app,
                "bpy.app.translations": fake_translations,
            },
    ):
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


draw_element = _load_draw_element_module()


def _load_draw_gesture_module():
    ops_package = _module(f"{PACKAGE}.ops")
    ops_package.__path__ = [str(ROOT / "ops")]
    quick_add_package = _module(f"{PACKAGE}.ops.quick_add")
    quick_add_package.__path__ = [str(ROOT / "ops" / "quick_add")]
    export_import = _module(
        f"{PACKAGE}.ops.export_import",
        Export=type("Export", (), {"bl_idname": "wm.export"}),
        Import=type("Import", (), {"bl_idname": "wm.import"}),
    )
    ops_package.export_import = export_import
    _module(
        f"{PACKAGE}.ops.quick_add.gesture_preview",
        GesturePreview=_GesturePreview,
        GesturePreviewClose=_GesturePreviewClose,
        GesturePreviewFrozen=_GesturePreviewFrozen,
    )
    _module(
        f"{PACKAGE}.utils.session_state",
        SessionState=_PreviewSessionState,
    )
    _module(f"{PACKAGE}.utils.icons", ui_icon=lambda name: name)

    fake_bpy = types.ModuleType("bpy")
    fake_bpy.types = types.SimpleNamespace(UILayout=object)
    name = f"{PACKAGE}.preferences.draw_gesture"
    spec = importlib.util.spec_from_file_location(name, DRAW_GESTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with patch.dict(sys.modules, {"bpy": fake_bpy}):
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


draw_gesture = _load_draw_gesture_module()


class _OperatorProperties:
    def __init__(self, identifier: str, text: str):
        object.__setattr__(self, "identifier", identifier)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "values", {})

    def __setattr__(self, name, value):
        self.values[name] = value


class _LayoutRecorder:
    def __init__(self):
        object.__setattr__(self, "events", [])
        object.__setattr__(self, "buttons", [])

    def __setattr__(self, name, value):
        self.events.append(("set", name, value))
        object.__setattr__(self, name, value)

    def _container(self, kind, **kwargs):
        self.events.append((kind, kwargs))
        return self

    def box(self):
        return self._container("box")

    def column(self, **kwargs):
        return self._container("column", **kwargs)

    def row(self, **kwargs):
        return self._container("row", **kwargs)

    def split(self, **kwargs):
        return self._container("split", **kwargs)

    def label(self, **kwargs):
        self.events.append(("label", kwargs))

    def prop(self, _data, property_name, **kwargs):
        self.events.append(("prop", property_name, kwargs))

    def menu(self, menu_name, **kwargs):
        self.events.append(("menu", menu_name, kwargs))

    def separator(self, **kwargs):
        self.events.append(("separator", kwargs))

    def operator(self, identifier, *, text="", **kwargs):
        button = _OperatorProperties(identifier, text)
        self.buttons.append(button)
        self.events.append(("operator", identifier, text, kwargs))
        return button


class _TreeLayoutRecorder:
    def __init__(self, kind="root"):
        self.kind = kind
        self.children = []
        self.operations = []
        self.enabled = True

    def _container(self, kind, **kwargs):
        child = _TreeLayoutRecorder(kind)
        child.operations.append(("container_options", kwargs))
        self.children.append(child)
        return child

    def box(self):
        return self._container("box")

    def column(self, **kwargs):
        return self._container("column", **kwargs)

    def row(self, **kwargs):
        return self._container("row", **kwargs)

    def split(self, **kwargs):
        return self._container("split", **kwargs)

    def label(self, **kwargs):
        self.operations.append(("label", kwargs))

    def prop(self, _data, property_name, **kwargs):
        self.operations.append(("prop", property_name, kwargs))

    def menu(self, menu_name, **kwargs):
        self.operations.append(("menu", menu_name, kwargs))

    def separator(self, **kwargs):
        self.operations.append(("separator", kwargs))

    def operator(self, identifier, *, text="", **kwargs):
        self.operations.append(("operator", identifier, text, kwargs))
        return _OperatorProperties(identifier, text)


def _tree_shape(node):
    return (
        node.kind,
        tuple(operation[0] for operation in node.operations),
        tuple(_tree_shape(child) for child in node.children),
    )


def _layout_shape(events):
    return [
        (event[0], "<add-operator>", *event[2:])
        if event[0] == "operator"
        else event
        for event in events
    ]


def _dotted_name(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class FrozenElementAddDrawTests(unittest.TestCase):
    def setUp(self):
        global _PREF
        _PREF = types.SimpleNamespace(
            add_element_property=types.SimpleNamespace(
                is_have_add_child=True,
                relationship="ROOT",
                add_active_radio=False,
            ),
            active_element=None,
        )
        _PreviewSessionState.gesture_preview_active = False
        _PreviewSessionState.gesture_preview_scope = ""

    def test_frozen_draw_keeps_shape_and_text_but_uses_inert_buttons(self):
        normal = _LayoutRecorder()
        frozen = _LayoutRecorder()

        draw_element.DrawElement.draw_element_add_property(normal, frozen=False)
        draw_element.DrawElement.draw_element_add_property(frozen, frozen=True)

        self.assertEqual(_layout_shape(normal.events), _layout_shape(frozen.events))
        self.assertGreater(len(normal.buttons), 0)
        self.assertEqual(
            [button.text for button in normal.buttons],
            [button.text for button in frozen.buttons],
        )
        self.assertTrue(all(
            button.identifier == _RealAdd.bl_idname
            for button in normal.buttons
        ))
        self.assertTrue(all(
            button.identifier == _FrozenAdd.bl_idname
            for button in frozen.buttons
        ))
        self.assertTrue(all(button.values for button in normal.buttons))
        self.assertTrue(all(not button.values for button in frozen.buttons))

    def test_layout_add_controls_use_two_fixed_rows(self):
        layout = _TreeLayoutRecorder()

        draw_element.DrawElement.draw_element_add_property(layout)

        main_column = layout.children[0].children[0]
        self.assertEqual(
            [
                operation
                for operation in main_column.operations
                if operation[0] == "separator"
            ],
            [("separator", {"factor": 0.5})],
        )
        layout_column = main_column.children[-1]
        self.assertEqual(len(layout_column.children), 2)
        container_row, item_row = layout_column.children
        self.assertEqual(
            [
                operation[2]
                for operation in container_row.operations
                if operation[0] == "operator"
            ],
            ["Row", "Column", "Box"],
        )
        self.assertEqual(
            [
                operation[2]
                for child in item_row.children
                for operation in child.operations
                if operation[0] == "operator"
            ],
            ["Div", "Label"],
        )
        self.assertEqual(
            [
                operation[2]
                for operation in item_row.operations
                if operation[0] == "operator"
            ],
            ["Split"],
        )
        self.assertEqual(
            [operation[0] for operation in item_row.operations[-2:]],
            ["menu", "menu"],
        )

    def test_unavailable_layout_items_do_not_change_row_shape(self):
        unavailable = _TreeLayoutRecorder()
        draw_element.DrawElement.draw_element_add_property(unavailable)

        _PREF.add_element_property.relationship = "CHILD"
        _PREF.active_element = types.SimpleNamespace(
            is_child_gesture=False,
            is_selected_structure=True,
            is_layout_container=False,
        )
        available = _TreeLayoutRecorder()
        draw_element.DrawElement.draw_element_add_property(available)

        self.assertEqual(_tree_shape(unavailable), _tree_shape(available))
        unavailable_items = unavailable.children[0].children[0].children[-1].children[1]
        available_items = available.children[0].children[0].children[-1].children[1]
        self.assertEqual(
            [child.enabled for child in unavailable_items.children],
            [False, False],
        )
        self.assertEqual(
            [child.enabled for child in available_items.children],
            [True, True],
        )

    def test_frozen_operator_is_property_free_and_registered(self):
        tree = ast.parse(ELEMENT_CURE_PATH.read_text(encoding="utf-8"))
        outer = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ElementCURE"
        )
        frozen = next(
            node for node in outer.body
            if isinstance(node, ast.ClassDef) and node.name == "FrozenADD"
        )

        self.assertEqual(
            [_dotted_name(base) for base in frozen.bases],
            ["bpy.types.Operator"],
        )
        self.assertNotIn(
            "poll",
            {node.name for node in frozen.body if isinstance(node, ast.FunctionDef)},
        )
        self.assertFalse(any(isinstance(node, ast.AnnAssign) for node in frozen.body))

        registry = ast.parse(GESTURE_INIT_PATH.read_text(encoding="utf-8"))
        classes_list = next(
            node.value for node in registry.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "classes_list"
                for target in node.targets
            )
        )
        self.assertIn(
            "ElementCURE.FrozenADD",
            {_dotted_name(item) for item in classes_list.elts},
        )

    def test_element_panel_forwards_the_frozen_state(self):
        tree = ast.parse(DRAW_GESTURE_PATH.read_text(encoding="utf-8"))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _dotted_name(node.func).endswith("draw_element_add_property")
        ]

        self.assertEqual(len(calls), 1)
        frozen_keyword = next(
            keyword for keyword in calls[0].keywords
            if keyword.arg == "frozen"
        )
        self.assertIsInstance(frozen_keyword.value, ast.Name)
        self.assertEqual(frozen_keyword.value.id, "allow_frozen")

    def test_frozen_preview_operator_is_property_free_and_registered(self):
        tree = ast.parse(PREVIEW_PATH.read_text(encoding="utf-8"))
        frozen_classes = [
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "GesturePreviewFrozen"
        ]
        self.assertEqual(len(frozen_classes), 1)
        frozen = frozen_classes[0]

        self.assertEqual(
            [_dotted_name(base) for base in frozen.bases],
            ["bpy.types.Operator"],
        )
        self.assertNotIn(
            "poll",
            {node.name for node in frozen.body if isinstance(node, ast.FunctionDef)},
        )
        self.assertFalse(any(isinstance(node, ast.AnnAssign) for node in frozen.body))

        registry = ast.parse(OPS_INIT_PATH.read_text(encoding="utf-8"))
        operator_list = next(
            node.value for node in registry.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "operator_list"
                for target in node.targets
            )
        )
        self.assertIn(
            "GesturePreviewFrozen",
            {_dotted_name(item) for item in operator_list.elts},
        )

    def test_item_panel_always_draws_disabled_preview_row_while_paused(self):
        tree = ast.parse(PANEL_PATH.read_text(encoding="utf-8"))
        panel = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "GestureItemPanel"
        )
        draw = next(
            node for node in panel.body
            if isinstance(node, ast.FunctionDef) and node.name == "draw"
        )
        top_level_calls = [
            node.value for node in draw.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        ]
        preview_call = next(
            call for call in top_level_calls
            if _dotted_name(call.func).endswith("draw_gesture_preview_button")
        )
        frozen_keyword = next(
            keyword for keyword in preview_call.keywords
            if keyword.arg == "frozen"
        )
        self.assertEqual(_dotted_name(frozen_keyword.value.func), "bool")
        self.assertEqual(_dotted_name(frozen_keyword.value.args[0]), "msg")

        enabled_assignment = next(
            node for node in draw.body
            if isinstance(node, ast.Assign)
            and any(
                _dotted_name(target) == "preview_column.enabled"
                for target in node.targets
            )
        )
        self.assertIsInstance(enabled_assignment.value, ast.UnaryOp)
        self.assertIsInstance(enabled_assignment.value.op, ast.Not)
        self.assertEqual(_dotted_name(enabled_assignment.value.operand), "msg")

    def test_preview_to_gesture_freeze_keeps_preview_row_shape_and_text(self):
        global _PREF
        gesture = types.SimpleNamespace(name="Gesture")
        _PREF = types.SimpleNamespace(
            enabled=True,
            active_gesture=gesture,
            active_element=object(),
        )
        _PreviewSessionState.gesture_preview_active = True
        _PreviewSessionState.gesture_preview_scope = "ELEMENT"

        normal = _LayoutRecorder()
        draw_gesture.GestureDraw.draw_gesture_preview_button(normal)

        # The real preview has now been closed by gesture registration. Frozen
        # drawing must use the entry snapshot instead of this live state.
        _PreviewSessionState.gesture_preview_active = False
        _PreviewSessionState.gesture_preview_scope = ""
        frozen = _LayoutRecorder()
        draw_gesture.GestureDraw.draw_gesture_preview_button(
            frozen,
            active_gesture=gesture,
            active_element=_PREF.active_element,
            frozen=True,
            preview_active=True,
            preview_scope="ELEMENT",
        )

        self.assertEqual(_layout_shape(normal.events), _layout_shape(frozen.events))
        self.assertEqual(
            [event for event in frozen.events if event[0] == "label"],
            [("label", {"text": "Previewing Element", "icon": "HIDE_OFF"})],
        )
        self.assertEqual([button.text for button in frozen.buttons], ["Close Preview"])
        self.assertEqual(
            [button.identifier for button in frozen.buttons],
            [_GesturePreviewFrozen.bl_idname],
        )
        self.assertTrue(all(not button.values for button in frozen.buttons))


if __name__ == "__main__":
    unittest.main()
