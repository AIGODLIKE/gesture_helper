from __future__ import annotations

from bpy.props import StringProperty

from ..utils.public import get_debug
from ..utils.expression import evaluate_condition

poll: str = """Poll expression template
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
        """Try to evaluate poll bool; may raise."""
        poll_res = evaluate_condition(self.poll_string)
        if get_debug("poll"):
            print(f"poll_bool\t{poll_res}\t{self.poll_string}")
            print()
        return poll_res

    @property
    def __poll_bool_is_validity__(self) -> bool:
        """Return whether poll bool string is valid."""
        try:
            self.__try_call_poll_bool__
            return True
        except Exception as e:
            if get_debug("poll"):
                print("poll_bool_is_validity")
                print(self.poll_string)
                print(e.args)
                import traceback
                traceback.print_stack()
                traceback.print_exc()
                print()
            return False

    @property
    def __poll_exception_info__(self) -> str:
        """Return poll error message."""
        try:
            self.__try_call_poll_bool__
            return ""
        except Exception as e:
            return str(e.args)

    @property
    def poll_bool(self) -> bool:
        """Return current poll evaluation."""
        try:
            return self.__try_call_poll_bool__
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return False

    def update_poll_string(self, context):
        from ..utils.public_cache import PublicCacheFunc
        PublicCacheFunc.cache_clear()

    poll_string: StringProperty(name='Prerequisite', description=poll, update=update_poll_string)

    def __init_selected_structure__(self):
        self.poll_string = 'True'
