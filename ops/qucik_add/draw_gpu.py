from ...lib.bpu import BpuLayout, Quadrant
from ...ops.qucik_add.show_tips import GestureShowTips


class DrawGpu:
    def __init__(self):
        self.gesture_bpu = BpuLayout(Quadrant.LIFT)
        self.tips = GestureShowTips()

    def unregister_draw_fun(self):
        self.gesture_bpu.unregister_draw()
        self.tips.unregister_draw()

    def register_draw_fun(self):
        self.gesture_bpu.register_draw()
        self.tips.register_draw()

    def draw_run(self, ops, event) -> set:
        try:
            with self.gesture_bpu as bpu:
                bpu.offset_position = ops.offset_position - ops.offset
                bpu.mouse_position = ops.mouse_position
                for g in ops.pref.gesture.values()[::-1]:
                    o = bpu.operator("wm.context_set_int", g.name, active=g.is_active)
                    o.data_path = "window_manager.gesture_index"
                    o.value = g.index
                bpu.separator()
                bpu.label("选择手势")

                if bpu.check_event(event):
                    return {'RUNNING_MODAL'}
            with self.tips as tips:
                tips.label("在想要添加的操作符或属性上右键,点击添加到手势即可添加")
                tips.label("在3D视图工具栏选择元素")
                tips.label("手势编辑模式  空白处点击右键退出")
                if tips.check_event(event):
                    return {'FINISHED'}

        except Exception as e:
            self.gesture_bpu.unregister_draw()
            print(e.args)
            import traceback
            traceback.print_exc()
            traceback.print_stack()
