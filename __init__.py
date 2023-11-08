from .utils import register as reg

bl_info = {
    "name": "Gesture Helper",
    "description": "手势助手,可以快速的使用手势运行blender 操作符或是更改属性",
    "author": "AIGODLIKE Community(BlenderCN辣椒,小萌新)",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Tool Panel",
    "support": "COMMUNITY",
    # "category": "3D View",
}


def register():
    reg.register()


def unregister():
    reg.unregister()
