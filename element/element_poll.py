from __future__ import annotations

from bpy.props import StringProperty

from ..utils.string_eval import try_call_eval

poll = """poll表达式
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
            return try_call_eval(self.poll_string)
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return False

    poll_string: StringProperty(name='条件',
                                description=poll)

    def init_selected_structure(self):
        self.poll_string = 'True'
