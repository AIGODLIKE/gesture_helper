import bpy
from bpy.props import BoolProperty

from ..gesture import GestureKeymap
from ..utils.public import PublicOperator, PublicProperty, poll_message_active_gesture


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
    """CRUD operations for gestures."""

    class GesturePoll(PublicOperator, PublicProperty):

        @classmethod
        def poll(cls, _):
            return poll_message_active_gesture(cls)

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
            pref = self.pref
            add = pref.gesture.add()
            add.name = 'Gesture'
            GestureKeymap.key_restart()
            self.structure_changed(add)
            self.tag_redraw()
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = 'Remove gesture'
        bl_description = 'Ctrl Alt Shift + Click: Remove all gesture!!!'
        bl_options = {'REGISTER', 'UNDO'}

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.pref.gesture.clear()
                self.cache_clear()
                GestureKeymap.key_restart()
                return {'FINISHED'}
            elif self.pref.draw_property.gesture_remove_tips:
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
            return {'FINISHED'}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = 'Sort gesture'

        is_next: BoolProperty()

        def execute(self, _):
            gesture = self.pref.active_gesture
            self.pref.active_gesture.sort(self.is_next)
            self.structure_changed(gesture)
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'gesture.gesture_copy'
        bl_label = 'Copy gesture'

        def execute(self, _):
            source = self.active_gesture
            source_index = source.index_element if source and len(source.element) else 0
            source.copy()
            new_gesture = self.pref.gesture[-1]
            self.structure_changed(new_gesture)
            new_gesture.__fix_duplicate_name__()
            if len(new_gesture.element):
                from ..utils.selection import enforce_single_selection

                idx = min(source_index, len(new_gesture.element) - 1)
                enforce_single_selection(new_gesture.element[idx])
            return {'FINISHED'}
