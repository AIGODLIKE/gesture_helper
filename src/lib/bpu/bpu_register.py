"""Deprecated draw-handler registration (unused; preview uses GestureGpuDraw)."""

from ....utils.public import tag_redraw, debug_print


class BpuRegister:
    __draw_class__ = {}

    def register_draw(self):
        """No-op: BPU draw is hosted by GestureGpuDraw / preview modal."""
        debug_print("BpuRegister.register_draw is deprecated; ignored", key='operator')
        tag_redraw()

    def unregister_draw(self):
        """No-op companion for deprecated register_draw."""
        tag_redraw()
