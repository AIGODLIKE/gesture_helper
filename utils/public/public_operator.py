import bpy
from bpy.types import Operator
from mathutils import Vector

from . import CacheHandler


class PublicOperator(
    CacheHandler,
    Operator, ):
    @staticmethod
    def ops_id_name(string):
        return 'emm_operator.' + string

    event: bpy.types.Event
    context: bpy.types.Context
    _mouse_x: int
    _mouse_y: int

    @staticmethod
    def get_event_key(event):
        alt = event.alt
        shift = event.shift
        ctrl = event.ctrl

        not_key = ((not ctrl) and (not alt) and (not shift))

        only_ctrl = (ctrl and (not alt) and (not shift))
        only_alt = ((not ctrl) and alt and (not shift))
        only_shift = ((not ctrl) and (not alt) and shift)

        shift_alt = ((not ctrl) and alt and shift)
        ctrl_alt = (ctrl and alt and (not shift))

        ctrl_shift = (ctrl and (not alt) and shift)
        ctrl_shift_alt = (ctrl and alt and shift)
        return not_key, only_ctrl, only_alt, only_shift, shift_alt, ctrl_alt, ctrl_shift, ctrl_shift_alt

    def set_event_key(self):
        (self.not_key,
         self.only_ctrl,
         self.only_alt,
         self.only_shift,
         self.shift_alt,
         self.ctrl_alt,
         self.ctrl_shift,
         self.ctrl_shift_alt) = self.get_event_key(
            self.event)

    def _set_ce(self, context, event):
        self.context = context
        self.event = event
        self.set_event_key()

    def _set_mouse(self, context, event, key):
        setattr(self, f'{key}_mouse_x', min(max(0, event.mouse_region_x), context.region.width))
        setattr(self, f'{key}_mouse_y', min(max(0, event.mouse_region_y), context.region.height))

    def init_invoke(self, context, event) -> None:
        self._set_ce(context, event)
        self._set_mouse(context, event, '_start')

    def init_modal(self, context, event) -> None:
        self._set_ce(context, event)
        self._set_mouse(context, event, '')

    @property
    def mouse_co(self) -> Vector:
        return Vector((self._mouse_x, self._mouse_y))

    @property
    def start_mouse_co(self) -> Vector:
        return Vector((self._start_mouse_x, self._start_mouse_y))
