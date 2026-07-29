from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "utils" / "translate.py"


def _load_translate_module(interface, tooltip, contexts):
    bpy = types.ModuleType("bpy")
    app = types.ModuleType("bpy.app")
    translations = types.ModuleType("bpy.app.translations")
    translations.pgettext_iface = interface
    translations.pgettext_tip = tooltip
    translations.contexts = contexts
    app.translations = translations
    bpy.app = app

    modules = {
        "bpy": bpy,
        "bpy.app": app,
        "bpy.app.translations": translations,
    }
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(
            "_rna_translation_context_test",
            MODULE_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module, modules


class RnaTranslationContextTests(unittest.TestCase):
    def test_explicit_property_context_does_not_fall_back_to_other_contexts(self):
        calls = []

        def translate(text, context=None):
            calls.append((text, context))
            if context == "WRONG_CONTEXT":
                return "错误译名"
            return text

        module, modules = _load_translate_module(
            translate,
            translate,
            ("WRONG_CONTEXT",),
        )

        with patch.dict(sys.modules, modules):
            self.assertEqual(
                module.translate_rna_text("Property Name", "PROPERTY_CONTEXT"),
                "Property Name",
            )
        self.assertEqual(calls, [("Property Name", "PROPERTY_CONTEXT")])

    def test_explicit_property_context_is_used_for_tooltips(self):
        interface_calls = []
        tooltip_calls = []

        def interface(text, context=None):
            interface_calls.append((text, context))
            return "interface"

        def tooltip(text, context=None):
            tooltip_calls.append((text, context))
            return "属性说明" if context == "PROPERTY_CONTEXT" else text

        module, modules = _load_translate_module(
            interface,
            tooltip,
            ("WRONG_CONTEXT",),
        )

        with patch.dict(sys.modules, modules):
            self.assertEqual(
                module.translate_rna_text(
                    "Property description",
                    "PROPERTY_CONTEXT",
                    tooltip=True,
                ),
                "属性说明",
            )
        self.assertEqual(
            tooltip_calls,
            [("Property description", "PROPERTY_CONTEXT")],
        )
        self.assertEqual(interface_calls, [])

    def test_explicit_context_does_not_use_a_context_free_api_fallback(self):
        def one_argument_translation(_text):
            return "无上下文译名"

        module, modules = _load_translate_module(
            one_argument_translation,
            one_argument_translation,
            (),
        )

        with patch.dict(sys.modules, modules):
            self.assertEqual(
                module.translate_rna_text("Property Name", "PROPERTY_CONTEXT"),
                "Property Name",
            )

    def test_missing_context_keeps_compatibility_fallback(self):
        calls = []

        def translate(text, context=None):
            calls.append((text, context))
            return "兼容译名" if context == "AVAILABLE_CONTEXT" else text

        module, modules = _load_translate_module(
            translate,
            translate,
            ("AVAILABLE_CONTEXT",),
        )

        with patch.dict(sys.modules, modules):
            self.assertEqual(
                module.translate_rna_text("Property Name", None),
                "兼容译名",
            )
        self.assertEqual(
            calls,
            [
                ("Property Name", None),
                ("Property Name", "AVAILABLE_CONTEXT"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
