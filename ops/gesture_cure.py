import bpy
from bpy.props import BoolProperty


class GestureCURE:
    """手势项 增删查改"""
    from ..utils.public import PublicOperator, PublicProperty

    class GesturePoll(PublicOperator, PublicProperty):

        @classmethod
        def poll(cls, _):
            return cls._pref().active_gesture is not None

    class ADD(PublicOperator, PublicProperty):
        bl_idname = 'gesture.gesture_add'
        bl_label = '添加手势'

        def execute(self, _):
            add = self.pref.gesture.add()
            self.cache_clear()
            add.name = 'Gesture'
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

        def invoke(self, context, event):
            return context.window_manager.invoke_confirm(
                self,
                event,
                title="确认删除手势?",
                message=f"{self.active_gesture.name}",
            )

        def execute(self, _):
            pref = self.pref
            act = pref.active_gesture
            act.key_unload()
            act.remove()
            act = pref.active_gesture
            if act:
                act.to_temp_kmi()
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, _):
            self.pref.active_gesture.sort(self.is_next)
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'gesture.gesture_copy'
        bl_label = '复制手势'

        def execute(self, _):
            self.active_gesture.copy()
            self.cache_clear()
            self.pref.gesture[-1].__check_duplicate_name__()
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}
