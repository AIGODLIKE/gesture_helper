from __future__ import annotations

from bpy.props import StringProperty

from ..utils.debug_util import debug_print, debug_trace_stack, debug_traceback
from ..utils.expression import evaluate_condition

_POLL_STRING_DESCRIPTION = "Leave empty to fail the poll (structure inactive)."

_POLL_CACHE_TIMER = None


def _schedule_poll_cache_clear():
    global _POLL_CACHE_TIMER
    from ..utils.public_cache import PublicCacheFunc

    def _flush():
        global _POLL_CACHE_TIMER
        _POLL_CACHE_TIMER = None
        PublicCacheFunc.clear_derived_only()
        return None

    cancel_poll_cache_timer()
    import bpy
    _POLL_CACHE_TIMER = _flush
    bpy.app.timers.register(_flush, first_interval=0.2)


def cancel_poll_cache_timer() -> None:
    """Cancel a pending poll-cache clear timer (call on unregister)."""
    global _POLL_CACHE_TIMER
    if _POLL_CACHE_TIMER is None:
        return
    try:
        import bpy
        if bpy.app.timers.is_registered(_POLL_CACHE_TIMER):
            bpy.app.timers.unregister(_POLL_CACHE_TIMER)
    except (ValueError, RuntimeError, AttributeError):
        ...
    _POLL_CACHE_TIMER = None


class ElementPoll:

    @property
    def __try_call_poll_bool__(self) -> bool:
        """Try to evaluate poll bool; may raise."""
        poll_res = evaluate_condition(self.poll_string)
        debug_print(f"poll_bool\t{poll_res}\t{self.poll_string}", key='poll')
        return poll_res

    @property
    def __poll_bool_is_validity__(self) -> bool:
        """Return whether poll bool string is valid."""
        try:
            self.__try_call_poll_bool__
            return True
        except Exception as e:
            debug_print("poll_bool_is_validity", key='poll')
            debug_print(self.poll_string, key='poll')
            debug_print(e.args, key='poll')
            debug_trace_stack(key='poll')
            debug_traceback(key='poll')
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
        except Exception:
            debug_traceback(key='poll')
            return False

    def update_poll_string(self, context):
        _schedule_poll_cache_clear()

    poll_string: StringProperty(
        name='Prerequisite',
        description=_POLL_STRING_DESCRIPTION,
        update=update_poll_string,
    )

    def __init_selected_structure__(self):
        self.poll_string = 'True'
