from bpy.props import IntProperty
from bpy.types import Operator


class RestoreKey(Operator):
    bl_idname = 'gesture.restore_key'
    bl_label = '重置快捷键'

    item_id: IntProperty(
        name="Item Identifier",
        description="Identifier of the item to restore",
    )

    @classmethod
    def poll(cls, context):
        keymap = getattr(context, "keymap", None)
        return keymap

    def execute(self, context):
        km = context.keymap
        kmi = km.keymap_items.from_id(self.item_id)

        print(self.bl_idname, kmi)
        km.restore_item_to_default(kmi)
        return {'FINISHED'}
