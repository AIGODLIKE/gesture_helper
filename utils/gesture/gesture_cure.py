from bpy.props import BoolProperty

from ..public import PublicOperator, PublicProperty


class GestureCURE:
    # TODO COPY Gesture
    # def copy(self, from_element):
    #     ...

    class GesturePoll(PublicOperator, PublicProperty):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_gesture is not None

    class ADD(PublicOperator, PublicProperty):
        bl_idname = 'gesture.gesture_add'
        bl_label = '添加手势'

        def execute(self, context):
            add = self.pref.gesture.add()
            add.name = 'Gesture'
            return {"FINISHED"}

    class REMOVE(GesturePoll):
        bl_idname = 'gesture.gesture_remove'
        bl_label = '删除手势'

        def execute(self, context):
            act = self.pref.active_gesture
            act.key_unload()
            act.remove()
            return {"FINISHED"}

    class SORT(GesturePoll):
        bl_idname = 'gesture.gesture_sort'
        bl_label = '排序手势'

        is_next: BoolProperty()

        def execute(self, context):
            self.pref.active_gesture.sort(self.is_next)
            return {"FINISHED"}
