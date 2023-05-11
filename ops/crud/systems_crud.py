import bpy
from bpy.props import StringProperty, BoolProperty

from ...utils.public import PublicOperator


class SystemOps:
    class Add(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_add')
        bl_label = 'Add System'
        add_type: StringProperty()
        add_name: StringProperty(default='New System')

        def execute(self, context):
            add = self.systems.add()
            add.name = self.add_name
            return {'FINISHED'}

    class Del(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_del')
        bl_label = 'Del System'
        bl_description = 'Del'
        'by Tag'  # TODO
        'by Active'
        'by Selected'  # TODO

        def execute(self, context):
            if self.active_system:
                self.active_system.remove()
            return {'FINISHED'}

    class Copy(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_copy')
        bl_label = 'Copy System'

        def execute(self, context):
            if self.active_system:
                self.active_system.copy()
            return {'FINISHED'}

    class Move(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_move')
        bl_label = 'Move System'

        is_next: BoolProperty()

        def execute(self, context):
            if self.active_system:
                self.active_system.move(self.is_next)
            return {'FINISHED'}

    class Export(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_export')
        bl_label = 'Export System'

        def execute(self, context):
            if self.active_system:
                self.active_system.copy()
            return {'FINISHED'}

    class Import(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_import')
        bl_label = 'Import System'

        def execute(self, context):
            if self.active_system:
                self.active_system.imoprt()
            return {'FINISHED'}


classes_tuple = (
    SystemOps.Add,
    SystemOps.Del,
    SystemOps.Copy,
    SystemOps.Move,
    SystemOps.Export,
    SystemOps.Import,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
