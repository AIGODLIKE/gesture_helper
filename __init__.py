from . import register_mod

bl_info = {
    "name": "Gesture Helper",
    "description": "Use gestures to run Blender operators or change properties.",
    "author": "ACGGIT Community",
    "version": (2, 3, 6),
    "blender": (4, 2, 0),
    "location": "View3D Sidebar",
    "support": "COMMUNITY",
    "category": "User Interface",
}

ADDON_VERSION = bl_info['version']


def register():
    register_mod.register()


def unregister():
    register_mod.unregister()
