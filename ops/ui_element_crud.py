import bpy
from bpy.props import BoolProperty, BoolVectorProperty, IntProperty, StringProperty

from ..utils.public import PublicClass
from ..utils.public.public_data import ElementType, PublicData, PublicPoll
from ..utils.public.public_operator import PublicOperator
from ..utils.public.public_ui import PublicPopupMenu, PublicUi


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
                return act_el.type.lower() in cls.TYPE_ALLOW_CHILD + ['child_gestures', ]
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


class ElementSetPollExpression(PublicUi,
                               PublicData,
                               PublicPoll,
                               PublicOperator,
                               ):
    bl_idname = PublicOperator.ops_id_name('set_poll_expression')
    bl_label = '设置条件表达式'

    is_popup_menu: BoolProperty(default=True, **PublicData.PROP_DEFAULT_SKIP)
    width: IntProperty(default=1000)

    is_not: BoolProperty(name='取反', description='可以理解成取反')
    is_set_item_poll: BoolProperty(name='是设置一个项的poll',
                                   )

    poll_string: StringProperty(
        name='条件',
        default='True',
    )

    def draw_logical_operator(self, layout: 'bpy.types.UILayout'):

        is_draw, lay = self.draw_extend_ui(layout,
                                           f'draw_logical_operator',
                                           label='语法解释',
                                           default_extend=False,
                                           )
        if is_draw:
            text = '可使用Python逻辑运算符或表达式'
            lay.label(text=text)
            text = '  and     x and y 布尔"与" - 如果 x 为 False，x and y 返回 x 的值，否则返回 y 的计算值 . '
            lay.label(text=text)
            text = '  or       x or y 布尔"或" - 如果 x 是 True，它返回 x 的值，否则它返回 y 的计算值 .'
            lay.label(text=text)
            text = '  not      not x 布尔"非" - 如果 x 为 True，返回 False  .如果 x 为 False，它返回 True .'
            lay.label(text=text)

            lay.separator()
            text = '''参数:'''
            lay.label(text=text)

            texts = {'bpy: bpy,': '',
                     'C: bpy.context,': 'blender 上下文',
                     'D: bpy.data,': 'blender数据',
                     'O: bpy.context.object,': '活动物体',
                     'mode: C.mode,': '模式',
                     'tool: C.tool_settings,': '工具设置',
                     'mesh: bpy.context.object.data,': '网格,如果物体不为mesh则为None',
                     'is_select_vert: bool,': '是否选择了顶点的布尔值', }
            for k, v in texts.items():
                sp = lay.split(factor=0.2)
                sp.label(text='    ' + k)
                sp.label(text=v)

            # long_label(lay, text, max_len=500)
        else:

            layout.separator()

            row = layout.row(align=True)
            row.prop(self, 'is_not')

            self.draw_list_items(layout)

    @property
    def item(self):
        return self.active_ui_element

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        sp = col.split(factor=0.05, align=True)
        sp.label(text='条件:')
        sp.prop(self.item, 'poll_string', text='')
        self.draw_logical_operator(col)

    def draw_list_items(self, layout: 'bpy.types.UILayout'):
        row = layout.row()
        for items in self.POLL_ALL_LIST:
            if not items:
                row.separator()
            else:
                col = row.column(align=True)
                self.draw_items(col, items)

    def draw_items(self, layout: 'bpy.types.UILayout', data):
        layout.label(text=data['name'])
        for item in data['items']:
            if not item:
                layout.separator()
            else:
                self.draw_item(layout, item, data)

    def draw_item(self, layout: 'bpy.types.UILayout', item, data):
        op = layout.operator(self.bl_idname,
                             text=item['name']
                             )
        is_parentheses = item.get('parentheses', True)

        prefix = item.get('prefix', data['prefix'])
        suffix = item.get('suffix', data['suffix'])
        is_not = 'not ' if self.is_not else ''

        d = item['item']
        ite = f'"{d}"' if (isinstance(d, str) and (
            not item.get('not_str'))) else str(d)

        poll_string = is_not + prefix + ite + suffix
        if is_parentheses:
            poll_string = '(' + poll_string + ')'

        op.is_not = self.is_not
        op.is_popup_menu = False
        op.poll_string = poll_string
        op.is_set_item_poll = self.is_set_item_poll

    def invoke(self, context, event):
        if not self.is_popup_menu:
            return self.execute(context)

        data = {'operator': self}
        if self.width != -1:
            data['width'] = self.width
        return context.window_manager.invoke_props_dialog(**data)

    def execute(self, context):
        if not self.is_popup_menu:
            print(self, 'execute', self.poll_string)
            act = self.item

            if act.poll_string == 'True':
                act.poll_string = self.poll_string
            else:
                act.poll_string += self.poll_string

        return {'FINISHED'}


classes_tuple = (
    ElementCRUD.Add,
    ElementCRUD.Del,
    ElementCRUD.Copy,
    ElementCRUD.Move,
    ElementCRUD.Refresh,

    ElementSetPollExpression,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
