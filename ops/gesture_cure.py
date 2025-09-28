import bpy
from bpy.props import BoolProperty

from ..gesture import GestureKeymap


def add_all_preset():
    from ..utils.preset import get_preset_gesture_list
    count = 0
    for k, v in get_preset_gesture_list().items():
        bpy.ops.gesture.gesture_import(
            filepath=v,
            run_execute=True,
        )
        count += 1
    return count


class GestureCURE:
    """手势项 增删查改"""
    from ..utils.public import PublicOperator, PublicProperty

    class GesturePoll(PublicOperator, PublicProperty):

        @classmethod
        def poll(cls, _):
            return cls._pref().active_gesture is not None

    class ADD(PublicOperator, PublicProperty):
        bl_idname = 'gesture.gesture_add'
        bl_label = 'Add gesture'
        bl_description = 'Ctrl Alt Shift + Click: Add all preset gesture!!!'

        def invoke(self, context, event):
            if event.ctrl and event.alt and event.shift:
                count = add_all_preset()
                self.report({'INFO'}, f"Import preset {count}")
                return {'FINISHED'}
            return self.execute(context)

        def execute(self, _):
            add = self.pref.gesture.add()
            self.cache_clear()
            add.name = 'Gesture'
            GestureKeymap.key_restart()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = 'Remove gesture'
        bl_description = 'Ctrl Alt Shift + Click: Remove all gesture!!!'

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                gesture = self.pref.gesture
                while len(gesture):
                    gesture[0].remove()
                    self.cache_clear()
                GestureKeymap.key_restart()
                bpy.ops.wm.save_userpref()
                return {'FINISHED'}
            if self.pref.draw_property.gesture_remove_tips:
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Confirm deletion gesture?",
                    message=f"{self.active_gesture.name}",
                )
            return self.execute(context)

        def execute(self, _):
            pref = self.pref
            act = pref.active_gesture
            act.remove()
            act = pref.active_gesture
            if act:
                act.to_temp_kmi()
            self.cache_clear()
            GestureKeymap.key_restart()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = 'Sort gesture'

        is_next: BoolProperty()

        def execute(self, _):
            self.pref.active_gesture.sort(self.is_next)
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'gesture.gesture_copy'
        bl_label = 'Copy gesture'

        def execute(self, _):
            self.active_gesture.copy()
            self.cache_clear()
            self.pref.gesture[-1].__fix_duplicate_name__()
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}
