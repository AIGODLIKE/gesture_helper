import json
import os.path

import bpy
from bpy.app.translations import pgettext

from ...utils.debug_util import debug_print

__translate__ = {}
__language_list__ = []

# Folder name under src/translate/ -> Blender locale id
_LOCALE_ALIASES = {
    "zh_CN": "zh_HANS",
}


def ___translate_id___() -> str:
    language = bpy.context.preferences.view.language
    if language in ('zh_HANS', 'zh_CN'):
        return "zh_CN"
    return language


def ___translate_dict___(key: str) -> dict:
    ti = ___translate_id___()
    if ti in __translate__:
        if key == "ALL":
            data = dict()
            for i in __translate__[ti]:
                for k, v in __translate__[ti][i].items():
                    data[k] = v
            return data
        elif key in __translate__[ti]:
            return __translate__[ti][key]
    return dict()


def __preset_translate__(name: str) -> str:
    """Translate preset names."""
    if bpy.context.preferences.view.use_translate_interface:
        preset = ___translate_dict___("preset")
        return preset[name] if (name in preset) else name
    return name


def __name_translate__(name: str) -> str:
    """Translate display names via add-on JSON + Blender translation contexts."""
    from ...utils.public import get_pref

    interface = bpy.context.preferences.view.use_translate_interface
    name_translate = get_pref().draw_property.enable_name_translation
    if interface and name_translate:
        translate_dict = ___translate_dict___("ALL")
        if name in translate_dict:
            return translate_dict[name]
        pn = pgettext(name)
        if pn != name:
            return pn
        for i in bpy.app.translations.contexts:
            text = pgettext(name, i)
            if name != text:
                return text
    return name


def __keymap_translate__(string: str) -> str:
    """Translate keymap labels."""
    if bpy.context.preferences.view.use_translate_interface:
        keymap = ___translate_dict___("keymap")
        return keymap[string] if (string in keymap) else pgettext(string)
    return string


def __load_json__():
    """Load translation JSON from locale subfolders."""
    global __translate__
    for root, _, files in os.walk(os.path.dirname(__file__)):
        for file in files:
            if not file.endswith('.json'):
                continue
            try:
                language = os.path.basename(root)
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not data:
                    continue
                bucket = __translate__.setdefault(language, {})
                bucket[file[:-5]] = data
            except Exception as e:
                debug_print("Failed to load language file", e.args, file, key='operator')


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
    global __translate__
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


def unregister():
    global __translate__
    __translate__.clear()
    for helper in __language_list__:
        helper.unregister()
    __language_list__.clear()
