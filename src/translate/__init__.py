import os.path
from functools import lru_cache

import bpy
from bpy.app.translations import pgettext

from ...utils.debug_util import debug_print
from ...utils.strict_json import load_json_strict

__translate__ = {}
__language_list__ = []

# Folder name under src/translate/ -> Blender locale id
_LOCALE_ALIASES = {
    "zh_CN": "zh_HANS",
}

_TRANSLATION_RESULT_CACHE_SIZE = 4096


def _translate_id_for_language(language: str) -> str:
    if language in ('zh_HANS', 'zh_CN'):
        return "zh_CN"
    return language


def ___translate_id___() -> str:
    return _translate_id_for_language(bpy.context.preferences.view.language)


@lru_cache(maxsize=None)
def _merged_translate_dict(language: str) -> dict:
    data = {}
    for category in __translate__.get(language, {}).values():
        data.update(category)
    return data


def _translate_dict_for_language(language: str, key: str) -> dict:
    categories = __translate__.get(language)
    if categories is None:
        return {}
    if key == "ALL":
        return _merged_translate_dict(language)
    return categories.get(key, {})


def ___translate_dict___(key: str) -> dict:
    return _translate_dict_for_language(___translate_id___(), key)


@lru_cache(maxsize=_TRANSLATION_RESULT_CACHE_SIZE)
def _cached_preset_translation(
        name: str,
        language: str,
        use_translate_interface: bool,
) -> str:
    if use_translate_interface:
        preset = _translate_dict_for_language(
            _translate_id_for_language(language),
            "preset",
        )
        return preset.get(name, name)
    return name


def __preset_translate__(name: str) -> str:
    """Translate preset names."""
    view = bpy.context.preferences.view
    return _cached_preset_translation(
        name,
        view.language,
        bool(view.use_translate_interface),
    )


@lru_cache(maxsize=_TRANSLATION_RESULT_CACHE_SIZE)
def _cached_name_translation(
        name: str,
        language: str,
        use_translate_interface: bool,
        enable_name_translation: bool,
) -> str:
    if not (use_translate_interface and enable_name_translation):
        return name

    translate_dict = _translate_dict_for_language(
        _translate_id_for_language(language),
        "ALL",
    )
    if name in translate_dict:
        return translate_dict[name]
    translated = pgettext(name)
    if translated != name:
        return translated
    for context in bpy.app.translations.contexts:
        translated = pgettext(name, context)
        if translated != name:
            return translated
    return name


def __name_translate__(name: str) -> str:
    """Translate display names via add-on JSON + Blender translation contexts."""
    from ...utils.public import get_pref

    view = bpy.context.preferences.view
    return _cached_name_translation(
        name,
        view.language,
        bool(view.use_translate_interface),
        bool(get_pref().draw_property.enable_name_translation),
    )


@lru_cache(maxsize=_TRANSLATION_RESULT_CACHE_SIZE)
def _cached_keymap_translation(
        string: str,
        language: str,
        use_translate_interface: bool,
) -> str:
    if not use_translate_interface:
        return string
    keymap = _translate_dict_for_language(
        _translate_id_for_language(language),
        "keymap",
    )
    if string in keymap:
        return keymap[string]
    contexts = bpy.app.translations.contexts
    for msgctxt in (
        contexts.ui_events_keymaps,
        contexts.id_screen,
        contexts.default,
    ):
        translated = pgettext(string, msgctxt)
        if translated != string:
            return translated
    return string


def __keymap_translate__(string: str) -> str:
    """Translate keymap labels.

    Prefer add-on keymap.json, then Blender's keymap / ID contexts.
    Avoid bare pgettext("Screen") which resolves to blend-mode「滤色」.
    """
    view = bpy.context.preferences.view
    return _cached_keymap_translation(
        string,
        view.language,
        bool(view.use_translate_interface),
    )


def _clear_translation_caches() -> None:
    _merged_translate_dict.cache_clear()
    _cached_preset_translation.cache_clear()
    _cached_name_translation.cache_clear()
    _cached_keymap_translation.cache_clear()


def __load_json__():
    """Load translation JSON from locale subfolders."""
    __translate__.clear()
    _clear_translation_caches()
    try:
        for root, _, files in os.walk(os.path.dirname(__file__)):
            for file in files:
                if not file.endswith('.json'):
                    continue
                try:
                    language = os.path.basename(root)
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = load_json_strict(f)
                    if not data:
                        continue
                    bucket = __translate__.setdefault(language, {})
                    bucket[file[:-5]] = data
                except Exception as e:
                    debug_print("Failed to load language file", e.args, file, key='operator')
    finally:
        _clear_translation_caches()


def get_language_list() -> tuple[str, ...]:
    """Return locale ids supported by the current Blender build."""
    try:
        prop = bpy.context.preferences.bl_rna.properties['view'].properties['language']
        return tuple(
            item.identifier for item in prop.enum_items
            if item.identifier != 'DEFAULT'
        )
    except Exception:
        return ('en_US', 'zh_HANS')


def _resolve_locale(folder_name: str, supported: tuple[str, ...]) -> str | None:
    """Map a translation folder name to a locale Blender accepts."""
    if folder_name in supported:
        return folder_name
    alias = _LOCALE_ALIASES.get(folder_name)
    if alias and alias in supported:
        return alias
    return None


def register():
    __load_json__()
    from .helper import TranslationHelper

    supported = get_language_list()
    for folder_name, translate_dict in __translate__.items():
        locale = _resolve_locale(folder_name, supported)
        if locale is None:
            debug_print(
                f"Skipping translations for unsupported locale folder: {folder_name}",
                key='operator',
            )
            continue
        for category, strings in translate_dict.items():
            ti = TranslationHelper(f"Gesture_{locale}_{category}", strings, lang=locale)
            ti.register()
            __language_list__.append(ti)
    _clear_translation_caches()


def unregister():
    __translate__.clear()
    for helper in __language_list__:
        helper.unregister()
    __language_list__.clear()
    _clear_translation_caches()
