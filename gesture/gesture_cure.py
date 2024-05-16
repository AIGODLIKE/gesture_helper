from bpy.props import BoolProperty

from ..utils.public import PublicOperator, PublicProperty
from ..utils.public_cache import cache_update_lock


class GestureCURE:
    @cache_update_lock
    def copy(self):
        from ..utils import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self)
        PropertySetUtils.set_prop(self.pref, 'gesture', {'0': copy_data})

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
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

        def execute(self, _):
            act = self.pref.active_gesture
            act.key_unload()
            act.remove()
            self.cache_clear()
            return {'FINISHED'}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, _):
            self.pref.active_gesture.sort(self.is_next)
            self.cache_clear()
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'gesture.gesture_copy'
        bl_label = '复制手势'

        def execute(self, _):
            self.active_gesture.copy()
            self.cache_clear()
            self.pref.gesture[-1].__check_duplicate_name__()
            self.cache_clear()
            return {'FINISHED'}
