import bpy
from bpy.props import StringProperty, BoolProperty

from ...utils.public import PublicOperator


class ElementOps:
    class Add(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_add')
        bl_label = 'Add Element'
        add_type: StringProperty()
        add_name: StringProperty(default='New Element')

        def invoke(self, context, event):
            if self.active_system:
                add = self.active_system.ui_element.add()
                add.name = self.add_name
                if event.ctrl:
                    ...
                else:
                    add.parent = self.active_ui_element
            return {'FINISHED'}

    class Del(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_del')
        bl_label = 'Del Element'
        bl_description = 'Del'
        'by Tag'  # TODO
        'by Active'
        'by Selected'  # TODO

        def execute(self, context):
            act = self.active_ui_element
            if act:
                act.remove()
            if act:
                ...
            return {'FINISHED'}

    class Copy(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_copy')
        bl_label = 'Copy Element'

        def execute(self, context):
            if self.active_ui_element:
                self.active_ui_element.copy()
            return {'FINISHED'}

    class Move(PublicOperator):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_move')
        bl_label = 'Move Element'

        is_next: BoolProperty()

        def invoke(self, context, event):
            active = self.active_ui_element
            if active:
                active.move(self.is_next)
            return {'FINISHED'}

    class Refresh(PublicOperator):
        bl_idname = PublicOperator.ops_id_name('element_refresh')
        bl_label = 'Refresh Element'

        def execute(self, context):
            act = self.active_ui_element
            if act:
                ...
            return {'FINISHED'}


classes_tuple = (
    ElementOps.Add,
    ElementOps.Del,
    ElementOps.Copy,
    ElementOps.Move,
    ElementOps.Refresh,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
