import bpy
from ....utils.debug_util import debug_print


class OperatorProperties:
    __data__ = dict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__data__ = dict()

    def __setattr__(self, key, value):
        if key != "__data__":
            self.__data__[key] = value
        else:
            super().__setattr__(key, value)

    def items(self):
        return self.__data__.items()

    @property
    def map(self):
        return self.__data__


class BpuOperator:
    __mouse_in_area__ = False

    __bl_idname__ = None  # Draw operator bl_idname

    __operator_properties__: OperatorProperties  # Operator props
    operator_context = 'INVOKE_DEFAULT'

    def __init__(self):
        self.__operator_properties__ = OperatorProperties()

    @property
    def __operator_func__(self) -> "bpy.types.Operator|None":
        if self.__bl_idname__:
            sp = self.__bl_idname__.split('.')
            if len(sp) == 2:
                prefix, suffix = sp
                func = getattr(getattr(bpy.ops, prefix), suffix)
                return func
        return None

    @property
    def __operator_text__(self) -> str:
        """Get operator display text."""
        try:
            fun = self.__operator_func__
            if fun:
                rn = fun.get_rna_type()
                if rn:
                    return rn.name
        except Exception as e:
            debug_print(f"__operator_text__ ERROR\t\n{self.__bl_idname__}\n", e, key='operator')
            from ....utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')

    def running_operator(self):
        try:
            func = self.__operator_func__
            if func:
                func(self.operator_context, True, **self.__operator_properties__.map)

                def g(v):
                    return f'"{v}"' if type(v) is str else v

                ops_property = ", ".join(
                    (f"{key}={g(value)}" for key, value in self.__operator_properties__.items()))
                debug_print(
                    f'running_operator bpy.ops.{self.__bl_idname__}'
                    f'("{self.operator_context}"{", " + ops_property if ops_property else ops_property})',
                    key='operator',
                )
        except Exception as e:
            from ....utils.debug_util import debug_traceback, debug_trace_stack
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            debug_print('running_operator ERROR', e, key='operator')
