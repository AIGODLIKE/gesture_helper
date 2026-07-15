from ...ops.quick_add.show_tips import GestureShowTips
from ...src.lib.bpu import BpuLayout, Quadrant
from ...utils.debug_util import debug_print


class DrawGpu:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gesture_bpu = BpuLayout(Quadrant.LIFT)
        self.gesture_bpu.font_size = 20
        self.tips = GestureShowTips()
        self._bpu_content_key = None

    def _gesture_content_key(self, gesture_list):
        return tuple(
            (g.index, bool(g.is_active), g.name, getattr(g, '__key_str__', ''))
            for g in gesture_list
        )

    def draw_run(self, ops, event) -> set:
        try:
            from ...src.translate import __name_translate__
            from ...utils.gesture_store import get_gestures
            gestures = get_gestures()
            gesture_list = list(gestures.values()) if gestures is not None else []
            content_key = self._gesture_content_key(gesture_list)
            offset = ops.offset_position - ops.offset
            mouse = ops.mouse_position

            if content_key != self._bpu_content_key or not self.gesture_bpu.__draw_children__:
                with self.gesture_bpu as bpu:
                    bpu.translate = False
                    bpu.offset_position = offset
                    bpu.mouse_position = mouse
                    if gesture_list:
                        for g in reversed(gesture_list):
                            name = f"{g.name}({g.__key_str__})"
                            o = bpu.operator("wm.context_set_int", name, active=g.is_active)
                            o.data_path = "window_manager.gesture_index"
                            o.value = g.index
                    else:
                        bpu.label(__name_translate__("No gestures. Please add one."), alert=True)
                    bpu.separator()
                    bpu.label(__name_translate__("Select Gesture"))
                self._bpu_content_key = content_key
            else:
                self.gesture_bpu.sync_input(offset, mouse)

            if self.gesture_bpu.check_event(event):
                return {'RUNNING_MODAL'}

            with self.tips as tips:
                tips.translate = True
                from bpy.app.translations import pgettext_iface
                for text in [
                    "Right-click on the operator or property you want to add and click Add to Gesture to add it.",
                    "Selecting elements in the 3D view toolbar",
                    "Gesture preview: Space-drag to move, right-click to exit"
                ]:
                    tips.label(pgettext_iface(text))
                if tips.check_event(event):
                    return {'FINISHED'}
        except Exception as e:
            debug_print(e.args, key='gpu')
            import traceback
            traceback.print_exc()
            traceback.print_stack()
