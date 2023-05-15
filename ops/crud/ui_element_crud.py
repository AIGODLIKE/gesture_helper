import bpy
from bpy.props import BoolProperty, BoolVectorProperty, StringProperty

from ...utils.public import PublicClass, PublicOperator
from ...utils.public.public_data import ElementType
from ...utils.public.public_ui import PublicPopupMenu


class ElementPoll:
    @classmethod
    def poll(cls, context):
        pref = PublicClass().pref
        return pref.active_ui_element


class ElementCRUD:
    class Add(PublicOperator,
              ElementType,
              PublicPopupMenu):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_add')
        bl_label = 'Add Element'
        bl_description = '''\n默认将会添加作为活动元素子级\nCtrl 添加在同级之下\nShift 添加到无父级'''

        add_name: StringProperty(default='New Element')
        event: BoolVectorProperty(size=3)

        def draw_menu(self, menu, context):
            col = menu.layout.column(align=True)
            col.operator_context = 'INVOKE_DEFAULT'
            for identifier, name, _ in self.enum_type_data:
                if len(identifier):
                    op = col.operator(self.bl_idname, text=name)
                    op.ui_type = self.ui_type
                    op.add_name = "New " + name
                    op.is_popup_menu = False
                    op.event = self.event

                    if self.is_select_structure_type:
                        op.select_structure_type = identifier
                    elif self.is_ui_layout_type:
                        op.ui_layout_type = identifier
                else:
                    col.separator()
                    col.label(text=name)

        def add_element(self, event: 'bpy.types.Event'):
            """通过Event判断添加方式"""
            ctrl = event.ctrl or self.event[0]
            alt = event.alt or self.event[1]
            shift = event.shift or self.event[2]
            if ctrl:
                self.add(self.active_ui_element.parent_collection_property)
            elif shift or not self.active_ui_element:
                self.add(self.active_system.ui_element)
            else:
                self.add(self.active_ui_element.children_element)

        def add(self, prop: 'bpy.props.CollectionProperty'):
            """向输入的属性集合添加项"""
            a = prop.add()
            a.ui_type = self.ui_type
            a.name = self.add_name
            a.ui_layout_type = self.ui_layout_type
            a.select_structure_type = self.select_structure_type

        def invoke(self, context, event):
            if self.is_popup_menu:
                self.event = [event.ctrl, event.alt, event.shift]
                return super().invoke(context, event)
            self.add_element(event)
            self.tag_redraw(context)
            return {'FINISHED'}

    class Del(PublicOperator,
              ElementPoll):  # TODO
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

    class Copy(PublicOperator,
               ElementPoll):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_copy')
        bl_label = 'Copy Element'

        def execute(self, context):
            if self.active_ui_element:
                self.active_ui_element.copy()
            return {'FINISHED'}

    class Move(PublicOperator,
               ElementPoll):  # TODO
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
    ElementCRUD.Add,
    ElementCRUD.Del,
    ElementCRUD.Copy,
    ElementCRUD.Move,
    ElementCRUD.Refresh,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
