from typing import Optional

import bpy
from mathutils import Vector


class BpuEvent:

    def __init__(self):
        self.mouse_position = Vector((0, 0))

    def click_event(self, event: bpy.types.Event) -> "BpuLayout":
        """判断是否有在此页面上"""
        ...
