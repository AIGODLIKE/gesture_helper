import bpy
from bpy.props import BoolProperty, BoolVectorProperty, StringProperty

from ..utils.public import PublicClass, PublicOperator
from ..utils.public.public_data import ElementType, PublicData
from ..utils.public.public_ui import PublicPopupMenu


class ElementPoll:
    @classmethod
    def poll(cls, context):
        pref = PublicClass().pref
        return pref.active_ui_element


class ElementCRUD:
    class Add(PublicOperator,
              ElementType,
              PublicData,
              PublicPopupMenu):  # TODO
        bl_idname = PublicOperator.ops_id_name('element_add')
        bl_label = 'Add Element'
        bl_description = '''\n默认将会添加作为活动元素子级\nCtrl 添加在同级之下\nShift 添加到无父级'''

        @classmethod
        def poll(cls, context):
            act_el = ElementPoll.poll(context)
            act_sys = cls.pref_().active_system
            if not act_el:
                return True
            elif act_sys.is_gesture_type:
                return act_el.type.lower() in cls.TYPE_ALLOW_CHILD + ['menu', ]
            return act_el.type.lower() in cls.TYPE_ALLOW_CHILD

        add_name: StringProperty(default='New Element')
        event: BoolVectorProperty(size=3)

        def is_have_child(self, identifier):
            act = self.active_ui_element
            if act:
                act_type = act.type.lower()
                if identifier in self.CANNOT_ACT_AS_CHILD:
                    return act_type in self.SELECT_STRUCTURE_ELEMENT
                return True
            else:
                return True

        def draw_menu(self, menu, context):
            col = menu.layout.column(align=True)
            col.operator_context = 'INVOKE_DEFAULT'
            for identifier, name, _ in self.enum_type_data:
                if len(identifier):
                    getattr(self, f'draw_add_{self.ui_type.lower()}', None)(col, identifier, name)

                else:
                    col.separator()
                    col.label(text=name)

        def draw_add_select_structure(self, layout, identifier, name):
            ops = self.draw_add_operator(layout, name)
            ops.select_structure_type = identifier

        def draw_add_ui_layout(self, layout, identifier, name):
            if self.is_have_child(identifier.lower()):
                op = self.draw_add_operator(layout, name)
                op.ui_layout_type = identifier

        def draw_add_gesture(self, layout, identifier, name):
            ops = self.draw_add_operator(layout, name)
            ops.gesture_type = identifier

        def draw_add_operator(self, layout, name):
            """添加操作符"""
            op = layout.operator(self.bl_idname, text=name)
            op.ui_type = self.ui_type
            op.add_name = "New " + name
            op.is_popup_menu = False
            op.event = self.event
            return op

        def add_element_ops(self, event: 'bpy.types.Event'):
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
            a.gesture_type = self.gesture_type
            a.parent_system.update_ui_layout()

        def invoke(self, context, event):
            if self.is_popup_menu:
                self.event = [event.ctrl, event.alt, event.shift]
                return super().invoke(context, event)
            self.add_element_ops(event)
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
