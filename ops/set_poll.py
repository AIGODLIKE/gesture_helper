import bpy
from bpy.props import StringProperty, BoolProperty

from ..utils.poll_data import PollData
from ..utils.public import PublicOperator, PublicProperty


class SetPollExpression(PublicProperty, PublicOperator, PollData):
    bl_label = 'Setting Conditional Expressions'
    bl_idname = 'gesture.set_poll_expression'

    is_not: BoolProperty(name='Invert', description='It can be interpreted as an inverse')

    poll_string: StringProperty(
        name='Prerequisite',
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    clear: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    ___notation___ = {
        '==': '!=',
        "is": 'not is',
        "in": 'not in',
    }
    __notation__ = {**___notation___, **{v: k for k, v in ___notation___}}

    @property
    def element(self):
        return self.active_element

    def draw_logical_operator(self, layout: 'bpy.types.UILayout'):
        from ..utils.public_ui import draw_extend_ui
        is_draw, lay = draw_extend_ui(layout,
                                      f'draw_logical_operator',
                                      label='Grammatical explanation',
                                      default_extend=False,
                                      )
        if is_draw:
            text = 'Can use Python logical operators or expressions'
            lay.label(text=text)
            text = "and  x and y Boolean 'and' - if x is False, x and y returns the value of x, otherwise it returns the calculated value of y"
            lay.label(text=text)
            text = "or   x or y Boolean 'or' - if x is True，return True，else return y"
            lay.label(text=text)
            text = "not  not x Boolean 'not' - if x is True，return False, if x is False return True"
            lay.label(text=text)

            lay.separator()
            lay.label(text="Parameters:")

            texts = {'bpy: bpy': '',
                     'C: bpy.context': 'Blender Context',
                     'D: bpy.data': 'Blender Data',
                     'O: bpy.context.object': 'Active Object',
                     'mode: C.mode': 'Context Mode',
                     'tool: C.tool_settings': 'Tool Settings',
                     'mesh: bpy.context.object.data': 'Mesh, None if the object is not a mesh',
                     # 'is_select_vert: bool': 'Whether or not the boolean value of the vertex is selected',
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

    def draw(self, _):
        layout = self.layout
        col = layout.column()
        is_alert = self.pref.active_element.is_alert
        cc = col.column(align=True)
        cc.alert = is_alert
        sp = cc.split(factor=0.05, align=True)
        sp.label(text='Prerequisite:')
        sp.prop(self.element, 'poll_string', text='')
        if is_alert:
            cc.label(text='Invalid expression', icon='ERROR')
            cc.operator_context = "EXEC_DEFAULT"
            cc.operator(self.bl_idname, text=self.__tn__("Clear")).clear = True
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

        is_parentheses = item.get('parentheses', data.get('parentheses', False))  # 是有小括号
        prefix = item.get('prefix', data.get('prefix', ''))  # 前缀
        suffix = item.get('suffix', data.get('suffix', ''))  # 后缀
        name = item.get('name', 'unknown')  # 名称
        notation = self.__get_notation__(item.get('notation', data.get('notation')))  # 符号

        info = item.get('item')
        is_not_str = item.get('not_str', data.get("not_str", False))
        string = f'"{info}"' if (isinstance(info, str) and (not is_not_str)) else str(info)

        prefix_string = f"{prefix}{' ' if prefix else ''}"
        suffix_string = f"{' ' if suffix else ''}{suffix}"
        poll_string = f"{prefix_string}{notation}{' ' if notation else ''}{string}{suffix_string} "
        if is_parentheses:
            poll_string = f'({poll_string})'

        layout.operator_context = "EXEC_DEFAULT"
        op = layout.operator(self.bl_idname, text=self.__tn__(name))
        op.poll_string = poll_string

    def invoke(self, context, _):
        data = {'operator': self, 'width': 1000}
        return context.window_manager.invoke_props_dialog(**data)

    def execute(self, context):
        act = self.element
        if self.clear:
            act.poll_string = 'True'
            return {"FINISHED"}
        if act.poll_string == 'True':
            act.poll_string = self.poll_string
        else:
            act.poll_string += self.poll_string
        return {'FINISHED'}

    def __get_notation__(self, notation: str) -> str:
        if self.is_not:
            if notation in self.__notation__:
                return self.__notation__[notation]
            return notation
        return notation
