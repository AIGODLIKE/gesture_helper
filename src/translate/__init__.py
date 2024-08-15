import json
import os.path

import bpy
from bpy.app.translations import pgettext

__translate__ = {}


def ___translate_id___() -> str:
    language = bpy.context.preferences.view.language
    if language in ('zh_HANS', 'zh_CN'):
        return "zh_CN"
    return language


def ___all_translate_dict___() -> dict:
    """获取所有翻译字典"""
    res = dict()
    ti = ___translate_id___()
    if ti in __translate__:
        for i in __translate__[ti].values():
            res.update(i)
    return res


def ___preset_translate_dict___() -> dict:
    """获取名称的翻译字典"""
    ti = ___translate_id___()
    if ti in __translate__:
        if "preset" in __translate__[ti]:
            return __translate__[ti]["preset"]
    return dict()


def __preset_translate__(name: str) -> str:
    """翻译名称"""
    name_dict = ___preset_translate_dict___()
    if name in name_dict:
        return name_dict[name]
    return name


def __translate_string__(string: str) -> str:
    """翻译"""
    at = ___all_translate_dict___()
    if string in at:
        return at[string]
    return pgettext(string)


def register():
    global __translate__
    folder = os.path.dirname(__file__)

    for root, dirs, files in os.walk(folder):
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
                    print("加载语言文件失败", e.args)


def unregister():
    global __translate__
    __translate__.clear()
