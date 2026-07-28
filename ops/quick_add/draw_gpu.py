from ...ops.quick_add.show_tips import GestureShowTips
from ...src.lib.overlay_layout import OverlayLayout
from ...utils.debug_util import debug_print


class DrawGpu:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gesture_bpu = OverlayLayout()
        self.gesture_bpu.anchor = 'RIGHT_CENTER'
        # Keep the selector compact so the viewport remains usable while
        # previewing the gesture.
        self.gesture_bpu.font_size = 12
        self.gesture_bpu.padding = 3
        self.gesture_bpu.min_row_height = 20
        self.gesture_bpu.gap = 2
        self.gesture_bpu.corner_radius = 4
        self.tips = GestureShowTips()
        self._bpu_content_key = None

    def _gesture_content_key(self, gesture_list):
        from ...src.translate import __name_translate__

        return tuple(
            (
                g.index,
                bool(g.is_active),
                g.name,
                __name_translate__(g.name),
                getattr(g, '__key_str__', ''),
            )
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
                    # Keep the exit action beside the selector title.  It is a
                    # compact utility action, rather than a full-width row.
                    with bpu.row() as title_row:
                        title_row.label(
                            __name_translate__("Select Gesture"), draggable=True,
                        )
                        title_row.operator(
                            "wm.gesture_preview_close",
                            __name_translate__("Exit Preview"),
                        )
                    bpu.separator()
                    if gesture_list:
                        for g in gesture_list:
                            name = f"{__name_translate__(g.name)}({g.__key_str__})"
                            o = bpu.operator("wm.context_set_int", name, active=g.is_active)
                            o.data_path = "window_manager.gesture_index"
                            o.value = g.index
                    else:
                        bpu.label(__name_translate__("No gestures. Please add one."), alert=True)
                self._bpu_content_key = content_key
            else:
                self.gesture_bpu.sync_input(offset, mouse)

            drag_revision = self.gesture_bpu.drag_revision
            interaction_revision = self.gesture_bpu.interaction_revision
            if self.gesture_bpu.check_event(event):
                if (
                        self.gesture_bpu.drag_revision != drag_revision
                        or self.gesture_bpu.interaction_revision != interaction_revision
                ):
                    if getattr(ops, '_preview_renderer', '') == 'MENU':
                        ops._tag_menu_redraw()
                    else:
                        ops.tag_redraw()
                return {'RUNNING_MODAL'}

            if not self.tips.root.children:
                with self.tips as tips:
                    from bpy.app.translations import pgettext_iface
                    for text in [
                        "Right-click an operator or property and choose Add to Gesture.",
                        "Edits in the Gesture panel update the preview live",
                        "Space-drag to move, right-click in the viewport to exit",
                    ]:
                        tips.label(pgettext_iface(text))
            if self.tips.check_event(event):
                return {'RUNNING_MODAL'}
        except Exception as e:
            debug_print(e.args, key='gpu')
            import traceback
            traceback.print_exc()
        return set()
