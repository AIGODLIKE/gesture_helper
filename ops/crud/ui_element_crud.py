import bpy
from bpy.props import StringProperty, BoolProperty

from ...utils.public import PublicOperator


class ElementAdd(PublicOperator):  # TODO
    bl_idname = PublicOperator.ops_id_name('element_add')
    bl_label = 'Add Element'
    add_type: StringProperty()
    add_name: StringProperty(default='New Element')

    def execute(self, context):
        if self.active_system:
            add = self.active_system.ui_element.add()
            add.name = self.add_name
        return {'FINISHED'}


class ElementDel(PublicOperator):  # TODO
    bl_idname = PublicOperator.ops_id_name('element_del')
    bl_label = 'Del Element'
    bl_description = 'Del'
    'by Tag'  # TODO
    'by Active'
    'by Selected'  # TODO

    def execute(self, context):
        if self.active_ui_element:
            self.active_ui_element.remove()
        return {'FINISHED'}


class ElementCopy(PublicOperator):  # TODO
    bl_idname = PublicOperator.ops_id_name('element_copy')
    bl_label = 'Copy Element'

    def execute(self, context):
        if self.active_ui_element:
            self.active_ui_element.copy()
        return {'FINISHED'}


class ElementMove(PublicOperator):  # TODO
    bl_idname = PublicOperator.ops_id_name('element_move')
    bl_label = 'Move Element'

    is_next: BoolProperty()

    def execute(self, context):
        if self.active_ui_element:
            self.active_ui_element.move(self.is_next)
        return {'FINISHED'}


classes_tuple = (
    ElementAdd,
    ElementDel,
    ElementCopy,
    ElementMove,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
