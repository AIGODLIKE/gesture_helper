from ...ops.qucik_add.show_tips import GestureShowTips
from ...src.lib.bpu import BpuLayout, Quadrant


class DrawGpu:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gesture_bpu = BpuLayout(Quadrant.LIFT)
        self.gesture_bpu.font_size = 20
        self.tips = GestureShowTips()

    def draw_run(self, ops, event) -> set:
        try:
            from ...src.translate import __name_translate__
            with self.gesture_bpu as bpu:
                bpu.translate = False
                bpu.offset_position = ops.offset_position - ops.offset
                bpu.mouse_position = ops.mouse_position
                gesture_list = ops.pref.gesture.values()
                if gesture_list:
                    for g in reversed(gesture_list):
                        name = f"{g.name}({g.__key_str__})"
                        o = bpu.operator("wm.context_set_int", name, active=g.is_active)
                        o.data_path = "window_manager.gesture_index"
                        o.value = g.index
                else:
                    bpu.label(__name_translate__("No Gestures, Please Add"), alert=True)
                bpu.separator()
                bpu.label(__name_translate__("Select Gesture"))

                if bpu.check_event(event):
                    return {'RUNNING_MODAL'}
            with self.tips as tips:
                tips.translate = True
                from bpy.app.translations import pgettext_iface
                for text in [
                    "Right-click on the operator or property you want to add and click Add to Gesture to add it.",
                    "Selecting elements in the 3D view toolbar",
                    "Gesture preview mode Blank space Right click to exit"
                ]:
                    tips.label(pgettext_iface(text))
                if tips.check_event(event):
                    return {'FINISHED'}
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_exc()
            traceback.print_stack()
