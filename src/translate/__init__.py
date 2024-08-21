import json
import os.path
import re

import bpy
from bpy.app.translations import pgettext

__translate__ = {}


def ___translate_id___() -> str:
    language = bpy.context.preferences.view.language
    if language in ('zh_HANS', 'zh_CN'):
        return "zh_CN"
    return language


def ___translate_dict__(key: str) -> dict:
    ti = ___translate_id___()
    if ti in __translate__:
        if key in __translate__[ti]:
            return __translate__[ti][key]
    return dict()


def __preset_translate__(name: str) -> str:
    """翻译预设"""
    preset = ___translate_dict__("preset")
    return preset[name] if (name in preset) else name


def __name_translate__(name: str) -> str:
    """翻译名称"""
    name_dict = ___translate_dict__("name")
    return name_dict[name] if (name in name_dict) else name


def __keymap_translate__(string: str) -> str:
    """翻译快捷键"""
    keymap = ___translate_dict__("keymap")
    return keymap[string] if (string in keymap) else pgettext(string)


def __load_json__():
    """加载翻译数据"""
    global __translate__
    for root, dirs, files in os.walk(os.path.dirname(__file__)):
        for file in files:
            if file.endswith('.json'):
                try:
                    language = os.path.basename(root)
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data:
                            if language in __translate__:
                                t = __translate__[language]
                            else:
                                t = __translate__[language] = dict()
                            t[file[:-5]] = data
                except Exception as e:
                    print("加载语言文件失败", e.args, file)


__language_list__ = []


def get_language_list() -> list:
    """
    Traceback (most recent call last):
  File "<blender_console>", line 1, in <module>
TypeError: bpy_struct: item.attr = val: enum "a" not found in ('DEFAULT', 'en_US', 'es', 'ja_JP', 'sk_SK', 'vi_VN', 'zh_HANS', 'ar_EG', 'de_DE', 'fr_FR', 'it_IT', 'ko_KR', 'pt_BR', 'pt_PT', 'ru_RU', 'uk_UA', 'zh_TW', 'ab', 'ca_AD', 'cs_CZ', 'eo', 'eu_EU', 'fa_IR', 'ha', 'he_IL', 'hi_IN', 'hr_HR', 'hu_HU', 'id_ID', 'ky_KG', 'nl_NL', 'pl_PL', 'sr_RS', 'sr_RS@latin', 'sv_SE', 'th_TH', 'tr_TR')
    """
    try:
        bpy.context.preferences.view.language = ""
    except TypeError as e:
        matches = re.findall(r'\(([^()]*)\)', e.args[-1])
        text = f"({matches[-1]})"
        return eval(text)


def register():
    global __translate__
    __load_json__()
    from .helper import TranslationHelper
    all_language = get_language_list()
    for language, translate_dict in __translate__.items():
        if "text" in translate_dict:
            if language not in all_language:
                if language == "zh_CN":
                    language = "zh_HANS"
                elif language == "zh_HANS":
                    language = "zh_CN"
            ti = TranslationHelper(f"Gesture_{language}", translate_dict["text"], lang=language)
            ti.register()
            __language_list__.append(ti)


def unregister():
    global __translate__
    __translate__.clear()
    for language in __language_list__:
        language.unregister()
