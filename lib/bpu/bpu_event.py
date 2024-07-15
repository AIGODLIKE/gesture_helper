import bpy
from mathutils import Vector


class BpuEvent:

    def __init__(self):
        self.mouse_position = Vector((0, 0))

    def update_event(self,event: bpy.types.Event):
        ...