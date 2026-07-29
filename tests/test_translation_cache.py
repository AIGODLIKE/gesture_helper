from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "src" / "translate" / "__init__.py"
PACKAGE = "_gesture_translation_cache_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class TranslationContexts:
    ui_events_keymaps = "keymap"
    id_screen = "screen"
    default = "default"

    def __iter__(self):
        return iter((self.default, self.ui_events_keymaps, self.id_screen))


view = types.SimpleNamespace(
    language="zh_HANS",
    use_translate_interface=True,
)
draw_property = types.SimpleNamespace(enable_name_translation=True)
translation_values = {}
pgettext_calls = []


def _pgettext(message, context=None):
    pgettext_calls.append((view.language, message, context))
    return translation_values.get((view.language, message, context), message)


class FakeTranslationHelper:
    def __init__(self, name, strings, lang):
        self.name = name
        self.strings = strings
        self.lang = lang
        self.registered = False
        self.unregistered = False

    def register(self):
        self.registered = True

    def unregister(self):
        self.unregistered = True


root_package = _module(PACKAGE)
root_package.__path__ = [str(MODULE_PATH.parents[2])]
src_package = _module(f"{PACKAGE}.src")
src_package.__path__ = [str(MODULE_PATH.parent.parent)]
utils_package = _module(f"{PACKAGE}.utils")
utils_package.__path__ = [str(MODULE_PATH.parents[2] / "utils")]
_module(f"{PACKAGE}.utils.debug_util", debug_print=lambda *_args, **_kwargs: None)
_module(
    f"{PACKAGE}.utils.public",
    get_pref=lambda: types.SimpleNamespace(draw_property=draw_property),
)
_module(
    f"{PACKAGE}.src.translate.helper",
    TranslationHelper=FakeTranslationHelper,
)

translations_module = _module(
    "bpy.app.translations",
    pgettext=_pgettext,
    contexts=TranslationContexts(),
)
app_module = _module("bpy.app", translations=translations_module)
bpy_module = _module(
    "bpy",
    app=app_module,
    context=types.SimpleNamespace(
        preferences=types.SimpleNamespace(view=view),
    ),
)

module_name = f"{PACKAGE}.src.translate"
spec = importlib.util.spec_from_file_location(
    module_name,
    MODULE_PATH,
    submodule_search_locations=[str(MODULE_PATH.parent)],
)
translate = importlib.util.module_from_spec(spec)
sys.modules[module_name] = translate
assert spec.loader is not None
spec.loader.exec_module(translate)


class TranslationCacheTests(unittest.TestCase):
    def setUp(self):
        view.language = "zh_HANS"
        view.use_translate_interface = True
        draw_property.enable_name_translation = True
        translation_values.clear()
        pgettext_calls.clear()
        translate.__translate__.clear()
        translate.__language_list__.clear()
        translate._clear_translation_caches()

    def test_merged_locale_dictionary_is_reused(self):
        translate.__translate__["zh_CN"] = {
            "first": {"Shared": "First", "One": "One translated"},
            "second": {"Shared": "Second"},
        }

        first = translate.___translate_dict___("ALL")
        second = translate.___translate_dict___("ALL")

        self.assertIs(first, second)
        self.assertEqual(first["Shared"], "Second")
        self.assertEqual(
            translate._merged_translate_dict.cache_info().hits,
            1,
        )

    def test_name_cache_tracks_language_interface_and_name_preference(self):
        translate.__translate__.update({
            "zh_CN": {"name": {"Action": "Action ZH"}},
            "en_US": {"name": {"Action": "Action EN"}},
        })

        self.assertEqual(translate.__name_translate__("Action"), "Action ZH")
        self.assertEqual(translate.__name_translate__("Action"), "Action ZH")
        self.assertEqual(translate._cached_name_translation.cache_info().hits, 1)

        view.language = "en_US"
        self.assertEqual(translate.__name_translate__("Action"), "Action EN")

        draw_property.enable_name_translation = False
        self.assertEqual(translate.__name_translate__("Action"), "Action")

        draw_property.enable_name_translation = True
        view.use_translate_interface = False
        self.assertEqual(translate.__name_translate__("Action"), "Action")

    def test_blender_name_context_scan_is_cached(self):
        translation_values[("zh_HANS", "Screen", "screen")] = "Screen ZH"

        self.assertEqual(translate.__name_translate__("Screen"), "Screen ZH")
        first_call_count = len(pgettext_calls)
        self.assertGreater(first_call_count, 1)

        self.assertEqual(translate.__name_translate__("Screen"), "Screen ZH")
        self.assertEqual(len(pgettext_calls), first_call_count)

    def test_keymap_and_preset_results_track_language_and_interface(self):
        translate.__translate__.update({
            "zh_CN": {"preset": {"Basic": "Basic ZH"}},
            "en_US": {"preset": {"Basic": "Basic EN"}},
        })
        translation_values[("zh_HANS", "Screen", "keymap")] = "Screen keymap ZH"
        translation_values[("en_US", "Screen", "keymap")] = "Screen keymap"

        self.assertEqual(translate.__preset_translate__("Basic"), "Basic ZH")
        self.assertEqual(translate.__preset_translate__("Basic"), "Basic ZH")
        self.assertEqual(translate.__keymap_translate__("Screen"), "Screen keymap ZH")
        keymap_call_count = len(pgettext_calls)
        self.assertEqual(translate.__keymap_translate__("Screen"), "Screen keymap ZH")
        self.assertEqual(len(pgettext_calls), keymap_call_count)

        view.language = "en_US"
        self.assertEqual(translate.__preset_translate__("Basic"), "Basic EN")
        self.assertEqual(translate.__keymap_translate__("Screen"), "Screen keymap")

        view.use_translate_interface = False
        self.assertEqual(translate.__preset_translate__("Basic"), "Basic")
        self.assertEqual(translate.__keymap_translate__("Screen"), "Screen")

    def test_loading_translation_files_invalidates_results(self):
        translation_values[("zh_HANS", "Dynamic", None)] = "Dynamic old"
        self.assertEqual(translate.__name_translate__("Dynamic"), "Dynamic old")

        translation_values[("zh_HANS", "Dynamic", None)] = "Dynamic new"
        self.assertEqual(translate.__name_translate__("Dynamic"), "Dynamic old")

        with patch.object(translate.os, "walk", return_value=[]):
            translate.__load_json__()

        self.assertEqual(translate.__name_translate__("Dynamic"), "Dynamic new")

    def test_register_and_unregister_invalidate_results(self):
        translate.__translate__["zh_CN"] = {"name": {"Dynamic": "Before register"}}
        self.assertEqual(translate.__name_translate__("Dynamic"), "Before register")

        def fake_load():
            translate.__translate__.clear()
            translate.__translate__["zh_CN"] = {"name": {"Dynamic": "After register"}}

        with (
            patch.object(translate, "__load_json__", side_effect=fake_load),
            patch.object(translate, "get_language_list", return_value=("zh_HANS",)),
        ):
            translate.register()

        self.assertEqual(translate.__name_translate__("Dynamic"), "After register")
        registered_helpers = tuple(translate.__language_list__)

        translation_values[("zh_HANS", "Dynamic", None)] = "After unregister"
        translate.unregister()

        self.assertEqual(translate.__name_translate__("Dynamic"), "After unregister")
        self.assertTrue(all(helper.unregistered for helper in registered_helpers))


if __name__ == "__main__":
    unittest.main()
