from ...ops.quick_add.show_tips import GestureShowTips
from ...src.lib.overlay_layout import OverlayLayout
from ...utils.debug_util import debug_print


class DrawGpu:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gesture_bpu = OverlayLayout()
        self.gesture_bpu.anchor = 'RIGHT_CENTER'
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

            if content_key != self._bpu_content_key or not self.gesture_bpu.root.children:
                with self.gesture_bpu as bpu:
                    bpu.sync_input(offset, mouse)
                    bpu.label(__name_translate__("Select Gesture"))
                    bpu.separator()
                    if gesture_list:
                        for g in gesture_list:
                            name = f"{g.name}({g.__key_str__})"
                            o = bpu.operator("wm.context_set_int", name, active=g.is_active)
                            o.data_path = "window_manager.gesture_index"
                            o.value = g.index
                    else:
                        bpu.label(__name_translate__("No gestures. Please add one."), alert=True)
                self._bpu_content_key = content_key
            else:
                self.gesture_bpu.sync_input(offset, mouse)

            if self.gesture_bpu.check_event(event):
                return {'RUNNING_MODAL'}

            if not self.tips.root.children:
                with self.tips as tips:
                    from bpy.app.translations import pgettext_iface
                    for text in [
                        "Right-click an operator or property and choose Add to Gesture.",
                        "Select elements from the 3D View toolbar",
                        "Gesture preview: Space-drag to move, right-click to exit",
                    ]:
                        tips.label(pgettext_iface(text))
            if self.tips.check_event(event):
                return {'RUNNING_MODAL'}
        except Exception as e:
            debug_print(e.args, key='gpu')
            import traceback
            traceback.print_exc()
        return set()
