from bpy.props import IntProperty

import bpy
class RestoreKey(bpy.types.Operator):
    bl_idname = 'wm.gesture_restore_key'
    bl_label = 'Restore Keymap'
    bl_description = 'Restore the active gesture keymap binding to its saved default'
    bl_options = {'REGISTER'}

    item_id: IntProperty(
        name="Item Identifier",
        description="Identifier of the item to restore",
    )

    @classmethod
    def poll(cls, context):
        keymap = getattr(context, "keymap", None)
        if keymap is None:
            cls.poll_message_set("Keymap editor context required")
            return False
        return True

    def execute(self, _):
        from ..utils.public import get_pref
        get_pref().active_gesture.restore_key()
        return {'FINISHED'}
