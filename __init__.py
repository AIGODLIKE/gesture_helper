from . import register_mod

bl_info = {
    "name": "Gesture Helper",
    "description": "Gesture Helper, which allows you to quickly use gestures to run the blender operator or change properties.",
    "author": "ACGGIT Community(小萌新)",
    "version": (2, 1, 9),
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
