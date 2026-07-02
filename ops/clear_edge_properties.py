"""Built-in operators replacing removed script element actions."""

import bpy


class ClearAllEdgeProperties(bpy.types.Operator):
    """Clear crease, bevel weight, seam, sharp, and freestyle edge data."""

    bl_idname = "wm.gesture_clear_all_edge_properties"
    bl_label = "Clear All Edge Properties"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH':
            cls.poll_message_set("Edit Mesh mode required")
            return False
        return True

    def execute(self, context):
        bpy.ops.transform.edge_crease('EXEC_DEFAULT', value=-1)
        bpy.ops.transform.edge_bevelweight('EXEC_DEFAULT', value=-1)
        bpy.ops.mesh.mark_seam(clear=True)
        bpy.ops.mesh.mark_sharp(clear=True)
        bpy.ops.mesh.mark_sharp(clear=True, use_verts=True)
        bpy.ops.mesh.mark_freestyle_edge(clear=True)
        return {'FINISHED'}
