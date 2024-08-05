from __future__ import annotations

from bpy.props import StringProperty
from typing import Any

from ..utils.string_eval import try_call_eval

poll: str = """poll表达式
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
    def __try_call_poll_bool__(self) -> bool:
        """尝试调用poll bool获取值
        可能会报错"""
        poll_res = try_call_eval(self.poll_string)
        if self.is_debug:
            print(f"poll_bool\t{poll_res}\t{self.poll_string}")
        return poll_res

    @property
    def __poll_bool_is_validity__(self) -> bool:
        """反回poll bool string 是否可用的布尔值"""
        try:
            self.__try_call_poll_bool__
            return True
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return False

    @property
    def poll_bool(self) -> bool:
        """反回当前self的poll

        Returns:
            bool: _description_
        """
        try:
            return self.__try_call_poll_bool__
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return False

    poll_string: StringProperty(name='条件', description=poll)

    def __init_selected_structure__(self):
        self.poll_string = 'True'
