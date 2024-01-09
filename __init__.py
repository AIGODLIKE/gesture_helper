from .utils import register as reg
import bpy
bl_info = {
    "name": "Gesture Helper",
    "description": "Gesture Assistant, which allows for quick execution of Blender operators or modification of properties using gestures.",
    "author": "AIGODLIKE Community(小萌新)",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Tool Panel",
    "support": "COMMUNITY",
    "category": "AIGODLIKE",
}

ADDON_VERSION = bl_info['version']

class TranslationHelper():
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()

        for src, src_trans in data.items():
            key = ("Operator", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ("*", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except(ValueError):
            pass

    def unregister(self):
        bpy.app.translations.unregister(self.name)


# Set
############
from . import zh_CN

GestureHelper_zh_CN = TranslationHelper('GestureHelper_zh_CN', zh_CN.data)
GestureHelper_zh_HANS = TranslationHelper('GestureHelper_zh_HANS', zh_CN.data, lang='zh_HANS')
def register():
    reg.register()
    if bpy.app.version < (4, 0, 0):
        GestureHelper_zh_CN.register()
    else:
        GestureHelper_zh_CN.register()
        GestureHelper_zh_HANS.register()

def unregister():
    reg.unregister()
    if bpy.app.version < (4, 0, 0):
        GestureHelper_zh_CN.unregister()
    else:
        GestureHelper_zh_CN.unregister()
        GestureHelper_zh_HANS.unregister()
