import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.app.translations import pgettext as _
from ..utils.poll_data import PollData
from ..utils.public import PublicOperator, PublicProperty


class SetPollExpression(PublicProperty, PublicOperator, PollData):
    bl_label = 'set poll expression'
    bl_idname = 'gesture.set_poll_expression'

    is_popup_menu: BoolProperty(default=True, **{'options': {'HIDDEN', 'SKIP_SAVE', }})
    width: IntProperty(default=1000)

    is_not: BoolProperty(name=_('negation'), description=_('negation'))
    is_set_item_poll: BoolProperty(name=_('Is to set the poll for an item'),
                                   )

    poll_string: StringProperty(
        name=_('condition'),
        default='True',
    )

    @property
    def element(self):
        return self.active_element

    def draw_logical_operator(self, layout: 'bpy.types.UILayout'):
        from ..utils.public_ui import draw_extend_ui
        is_draw, lay = draw_extend_ui(layout,
                                      f'draw_logical_operator',
                                      label='Grammatical explanations',
                                      default_extend=False,
                                      )
        if is_draw:
            text = _('Can use Python logical operators or expressions')
            lay.label(text=text)
            text = _("  and     x and y boolean 'and' - If x is False, x and y return the value of x, otherwise, return the computed value of y. ")
            lay.label(text=text)
            text = _("  or       x or y boolean 'or' - If x is True, it returns the value of x; otherwise, it returns the computed value of y")
            lay.label(text=text)
            text = _(" not      not x boolean 'not' - If x is True, returns False. If x is False, it returns True")
            lay.label(text=text)

            lay.separator()
            text = _('''parameter:''')
            lay.label(text=text)

            texts = {'bpy: bpy': '',
                     'C: bpy.context': 'blender context',
                     'D: bpy.data': 'blender data',
                     'O: bpy.context.object': 'active object',
                     'mode: C.mode': 'mode',
                     'tool: C.tool_settings': 'tool settings',
                     'mesh: bpy.context.object.data': 'Grid, None if the object is not a mesh',
                     # 'is_select_vert: bool': '是否选择了顶点的布尔值',
                     }
            for k, v in texts.items():
                sp = lay.split(factor=0.2)
                sp.label(text='    ' + k)
                sp.label(text=v)
        else:

            layout.separator()

            row = layout.row(align=True)
            row.prop(self, 'is_not')

            self.draw_list_items(layout)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        sp = col.split(factor=0.05, align=True)
        sp.label(text='condition:')
        sp.prop(self.element, 'poll_string', text='')
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
        if self.is_popup_menu:
            data = {'operator': self}
            if self.width != -1:
                data['width'] = self.width
            return context.window_manager.invoke_props_dialog(**data)
        else:
            return self.execute(context)

    def execute(self, context):
        if not self.is_popup_menu:
            act = self.element
            if act.poll_string == 'True':
                act.poll_string = self.poll_string
            else:
                act.poll_string += self.poll_string
        return {'FINISHED'}
