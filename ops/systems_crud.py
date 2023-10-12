import bpy
from bpy.props import StringProperty, BoolProperty

from ..public import PublicClass, PublicOperator, PublicPopupMenuOperator, PublicData


class SystemPoll:
    @classmethod
    def poll(cls, context):
        pref = PublicClass().pref
        return pref.active_system


class SystemCURD:
    class Add(PublicOperator,
              PublicPopupMenuOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_add')
        bl_label = 'Add System'
        add_type: StringProperty(default='GESTURE')
        add_name: StringProperty(default='New System')

        def draw_menu(self, menu, context):
            col = menu.layout.column(align=True)
            for i, name, _ in PublicData.ENUM_UI_SYSTEM_TYPE:
                ops = col.operator(self.bl_idname, text=name)
                ops.add_type = i
                ops.add_name = "New " + name
                ops.is_popup_menu = False

        def invoke(self, context, event):
            return self.execute(context)

        def execute(self, context):
            add = self.systems.add()
            add.name = self.add_name
            add.system_type = self.add_type
            return {'FINISHED'}

    class Del(PublicOperator,
              SystemPoll):  # TODO
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

    class Copy(PublicOperator,
               SystemPoll):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_copy')
        bl_label = 'Copy System'

        def execute(self, context):
            if self.active_system:
                self.active_system.copy()
            return {'FINISHED'}

    class Move(PublicOperator,
               SystemPoll):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_move')
        bl_label = 'Move System'

        is_next: BoolProperty()

        def execute(self, context):
            if self.active_system:
                self.active_system.move(self.is_next)
            return {'FINISHED'}

    class Export(PublicOperator,
                 SystemPoll):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_export')
        bl_label = 'Export System'

        def execute(self, context):
            if self.active_system:
                self.active_system.copy()
            return {'FINISHED'}

    class Import(PublicOperator, SystemPoll):  # TODO
        bl_idname = PublicOperator.ops_id_name('system_import')
        bl_label = 'Import System'

        def execute(self, context):
            if self.active_system:
                self.active_system.imoprt()
            return {'FINISHED'}


classes_tuple = (
    SystemCURD.Add,
    SystemCURD.Del,
    SystemCURD.Copy,
    SystemCURD.Move,
    SystemCURD.Export,
    SystemCURD.Import,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
