from bpy.props import IntProperty
from bpy.types import Operator


class RestoreKey(Operator):
    bl_idname = 'gesture.restore_key'
    bl_label = 'Restore key'

    item_id: IntProperty(
        name="Item Identifier",
        description="Identifier of the item to restore",
    )

    @classmethod
    def poll(cls, context):
        keymap = getattr(context, "keymap", None)
        return keymap

    def execute(self, _):
        from ..utils.public import get_pref
        get_pref().active_gesture.restore_key()
        return {'FINISHED'}
