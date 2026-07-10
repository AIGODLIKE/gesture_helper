import bpy
from bpy.props import BoolProperty

from ..gesture import GestureKeymap
from ..utils.public import (
    PublicOperator,
    PublicProperty,
    poll_addon_preferences,
    poll_message_active_gesture,
)


def add_all_preset():
    from ..utils.preset import get_preset_gesture_list
    count = 0
    for k, v in get_preset_gesture_list().items():
        bpy.ops.wm.gesture_import(
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
        bl_idname = 'wm.gesture_add'
        bl_label = 'Add gesture'
        bl_description = 'Hold Ctrl+Alt+Shift while clicking to import all bundled presets'
        bl_options = {'REGISTER'}

        @classmethod
        def poll(cls, context):
            return poll_addon_preferences(cls)

        def invoke(self, context, event):
            if event.ctrl and event.alt and event.shift:
                count = add_all_preset()
                self.report({'INFO'}, f"Import preset {count}")
                return {'FINISHED'}
            return self.execute(context)

        def execute(self, _):
            from ..utils.gesture_store import get_gesture_store, get_gestures
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None:
                return {'CANCELLED'}
            add = gestures.add()
            add.name = 'Gesture'
            store.index_gesture = len(gestures) - 1
            GestureKeymap.key_restart()
            self.structure_changed(add)
            self.tag_redraw()
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'wm.gesture_remove'
        bl_label = 'Remove gesture'
        bl_description = (
            'Hold Ctrl+Alt+Shift while clicking to remove all gestures. '
            'You will be asked to confirm. This cannot be undone.'
        )
        bl_options = {'REGISTER'}

        bulk_remove: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.bulk_remove = True
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Remove all gestures?",
                    message="This removes every gesture. This cannot be undone.",
                )
            self.bulk_remove = False
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
            from ..utils.gesture_store import get_gesture_store, get_gestures
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None:
                return {'CANCELLED'}
            if self.bulk_remove:
                gestures.clear()
                store.index_gesture = 0
                self.cache_clear()
                GestureKeymap.key_restart()
                self.bulk_remove = False
                return {'FINISHED'}
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
        bl_idname = 'wm.gesture_sort'
        bl_label = 'Sort gesture'
        bl_description = 'Move the active gesture up or down in the list'
        bl_options = {'REGISTER'}

        is_next: BoolProperty()

        def execute(self, _):
            gesture = self.pref.active_gesture
            self.pref.active_gesture.sort(self.is_next)
            self.structure_changed(gesture)
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'wm.gesture_copy'
        bl_label = 'Copy gesture'
        bl_description = 'Duplicate the active gesture and its elements'
        bl_options = {'REGISTER'}

        def execute(self, _):
            from ..utils.gesture_store import get_gesture_store, get_gestures
            source = self.active_gesture
            source_index = source.index_element if source and len(source.element) else 0
            source.copy()
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None or not len(gestures):
                return {'CANCELLED'}
            new_gesture = gestures[-1]
            store.index_gesture = len(gestures) - 1
            self.structure_changed(new_gesture)
            new_gesture.__fix_duplicate_name__()
            if len(new_gesture.element):
                from ..utils.selection import enforce_single_selection

                idx = min(source_index, len(new_gesture.element) - 1)
                enforce_single_selection(new_gesture.element[idx])
            return {'FINISHED'}
