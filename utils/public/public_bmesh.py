import bmesh
import bpy


class PublicBmesh:

    @classmethod
    def get_bmesh(cls, obj: bpy.types.Object) -> 'bmesh':
        if (not obj) or (obj.type != 'MESH'):
            return

        if obj.mode == 'EDIT':
            return bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            return bm
