import bpy
from bpy.props import StringProperty, BoolProperty

from ..utils.poll_data import PollData
from ..utils.public import PublicOperator, PublicProperty


class SetPollExpression(PublicProperty, PublicOperator, PollData):
    bl_label = '设置条件表达式'
    bl_idname = 'gesture.set_poll_expression'

    is_not: BoolProperty(name='取反', description='可以理解成取反')

    poll_string: StringProperty(
        name='条件',
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
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

            texts = {'bpy: bpy': '',
                     'C: bpy.context': 'blender 上下文',
                     'D: bpy.data': 'blender数据',
                     'O: bpy.context.object': '活动物体',
                     'mode: C.mode': '模式',
                     'tool: C.tool_settings': '工具设置',
                     'mesh: bpy.context.object.data': '网格,如果物体不为mesh则为None',
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

    def draw(self, _):
        layout = self.layout
        col = layout.column()
        sp = col.split(factor=0.05, align=True)
        sp.label(text='条件:')
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

        is_parentheses = item.get('parentheses', data.get('parentheses', False))  # 是有小括号
        prefix = item.get('prefix', data.get('prefix', ''))  # 前缀
        suffix = item.get('suffix', data.get('suffix', ''))  # 后缀
        name = item.get('name', 'unknown')  # 名称
        notation = self.__get_notation__(item.get('notation', data.get('notation')))  # 符号

        info = item.get('item')
        is_not_str = item.get('not_str', data.get("not_str", False))
        string = f'"{info}"' if (isinstance(info, str) and (not is_not_str)) else str(info)

        poll_string = f"{prefix} {notation} {string} {suffix}"
        if is_parentheses:
            poll_string = f'({poll_string})'

        layout.operator_context = "EXEC_DEFAULT"
        op = layout.operator(self.bl_idname, text=self._ts_(name))
        op.poll_string = poll_string

    def invoke(self, context, _):
        data = {'operator': self, 'width': 1000}
        return context.window_manager.invoke_props_dialog(**data)

    def execute(self, context):
        act = self.element
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
