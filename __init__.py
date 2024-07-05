from . import register_mod

bl_info = {
    "name": "Gesture Helper",
    "description": "手势助手,可以快速的使用手势运行blender 操作符或是更改属性",
    "author": "AIGODLIKE Community(小萌新)",
    "version": (1, 0, 3),
    "blender": (3, 0, 0),
    "location": "Tool Panel",
    "support": "COMMUNITY",
    "category": "幻之境",
}

ADDON_VERSION = bl_info['version']


def register():
    register_mod.register()


def unregister():
    register_mod.unregister()
