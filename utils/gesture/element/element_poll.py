from __future__ import annotations

import ast

import bpy
from bpy.props import StringProperty

poll = """poll expression
{'bpy': bpy,
'C': bpy.context,
'D': bpy.data,
'O': bpy.context.object,
'mode': bpy.context.mode,
'tool': bpy.context.tool_settings,
}
"""


class ElementPoll:
    @property
    def poll_bool(self) -> bool:
        """反回当前self的poll

        Returns:
            bool: _description_
        """

        try:
            poll = self._from_poll_string_get_bool(self.poll_string)
            return poll
        except Exception as e:
            print(f'ERROR:  poll_bool  {self.poll_string}\t', e.args, self.poll_args)
            return False

    poll_string: StringProperty(name='条件',
                                description=poll)

    @staticmethod
    def __is_enabled_addon__(addon_name):  # 测试是否启用此插件
        return addon_name in bpy.context.preferences.addons

    __globals = {"__builtins__": None,
                 'len': len,
                 'is_enabled_addon': __is_enabled_addon__,
                 #  'max':max,
                 #  'min':min,
                 }

    @property
    def poll_args(self):
        """反回poll eval的环境

        Returns:
            _type_: _description_
        """
        C = bpy.context
        D = bpy.data
        ob = bpy.context.object
        sel_objs = bpy.context.selected_objects
        use_sel_obj = ((not ob) and sel_objs)  # 使用选择的obj最后一个
        O = sel_objs[-1] if use_sel_obj else ob
        mesh = O.data if O else None

        return {'bpy': bpy,
                'C': C,
                'D': D,
                'O': O,
                'mode': C.mode,
                'tool': C.tool_settings,
                'mesh': mesh,
                }

    def _from_poll_string_get_bool(self, poll_string: str) -> bool:
        dump_data = ast.dump(ast.parse(poll_string), indent=2)
        shield = {'Del',
                  'Import',
                  'Lambda',
                  'Return',
                  'Global',
                  'Assert',
                  'ClassDef',
                  'ImportFrom',
                  #   'Module',
                  #   'Expr',
                  #   'Call',
                  }
        is_shield = {i for i in shield if i in dump_data}
        if is_shield:
            print(Exception(f'input poll_string is invalid\t{is_shield} of {poll_string}'))
            return False
        else:
            e = eval(poll_string, self.__globals, self.poll_args)
            return bool(e)

    def init_selected_structure(self):
        self.poll_string = 'True'
