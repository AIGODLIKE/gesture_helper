from bpy.props import BoolProperty

from ..public import PublicOperator, PublicProperty
from ..public_cache import cache_update_lock


class GestureCURE:
    @cache_update_lock
    def copy(self):
        from .. import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self)
        PropertySetUtils.set_prop(self.pref, 'gesture', {'0': copy_data})

    class GesturePoll(PublicOperator, PublicProperty):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_gesture is not None

    class ADD(PublicOperator, PublicProperty):
        bl_idname = 'gesture.gesture_add'
        bl_label = 'Add gesture'

        def execute(self, context):
            add = self.pref.gesture.add()
            self.cache_clear()
            add.name = 'Gesture'
            return {"FINISHED"}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = 'Delete gestures'

        def execute(self, context):
            act = self.pref.active_gesture
            act.key_unload()
            act.remove()
            self.cache_clear()
            return {"FINISHED"}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = 'Sort gestures'

        is_next: BoolProperty()

        def execute(self, context):
            self.pref.active_gesture.sort(self.is_next)
            self.cache_clear()
            return {"FINISHED"}

    class COPY(GesturePoll):
        bl_idname = 'gesture.gesture_copy'
        bl_label = 'Copy gestures'

        def execute(self, context):
            self.active_gesture.copy()
            self.cache_clear()
            self.pref.gesture[-1].__check_duplicate_name__()
            self.cache_clear()
            return {"FINISHED"}
