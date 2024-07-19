import bpy


class OperatorProperties(dict):
    ...


class BpuOperator:
    __active_operator__ = None  # 活动操作符
    __mouse_in_area__ = False

    __bl_idname__ = None  # 绘制的bl_idname

    __operator_properties__ = OperatorProperties()  # 操作属性
    operator_context = 'INVOKE_DEFAULT'

    @property
    def __operator_func__(self) -> "bpy.types.Operator":
        sp = self.__bl_idname__.split('.')
        if len(sp) == 2:
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            return func

    @property
    def __operator_text__(self) -> str:
        """获取操作符文本"""
        try:
            fun = self.__operator_func__
            if fun:
                rn = fun.get_rna_type()
                if rn:
                    return rn.name
        except Exception as e:
            print(f"__operator_text__ ERROR\t\n{self.__bl_idname__}\n", e)
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    def running_operator(self):
        try:
            func = self.__operator_func__
            if func:
                func(self.operator_context, True, **self.__operator_properties__)

                def g(v):
                    return f'"{v}"' if type(v) is str else v

                ops_property = ", ".join(
                    (f"{key}={g(value)}" for key, value in self.__operator_properties__.items()))
                print(
                    f'running_operator bpy.ops.{self.__bl_idname__}'
                    f'("{self.operator_context}"{", " + ops_property if ops_property else ops_property})',
                )
        except Exception as e:
            print('running_operator ERROR', e)
