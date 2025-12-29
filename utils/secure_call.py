import ast

import bpy


def __check_addon_is_enabled__(addon_name):
    """check addon enable state"""
    return addon_name in bpy.context.preferences.addons


__secure_call_globals__ = {
    "__builtins__": None,
    'len': len,
    'is_enabled_addon': __check_addon_is_enabled__,
    'print': print,
    'dict': dict,
    'list': list,
    'max': max,
    'min': min,
    'getattr': getattr,
    'hasattr': hasattr,
}


def __secure_call_args__():
    """
    Returns:
        _type_: _description_
    """
    C = bpy.context
    D = bpy.data
    ob = getattr(bpy.context, "object", None)
    sel_objs = getattr(bpy.context, "selected_objects", [])
    use_sel_obj = ((not ob) and sel_objs)  # use selected object if no active object
    active_object = sel_objs[-1] if use_sel_obj else ob
    data = active_object.data if active_object else None

    return {'bpy': bpy,

            'C': C,  # bpy.context
            'D': D,  # bpy.data
            'O': active_object,

            'data': data,
            'mode': C.mode,
            'tool': C.tool_settings,
            }


__shield_hazard_type__ = {'Del',
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


def __check_shield__(eval_string) -> bool:
    """当出现不允许的语法时反回False"""
    dump_data = ast.dump(ast.parse(eval_string), indent=2)
    is_shield = {i for i in __shield_hazard_type__ if i in dump_data}
    if is_shield:
        print(f'input poll_string is invalid\t{is_shield} of {eval_string}')
        return False
    return True


def secure_call_eval(eval_string: str):
    if __check_shield__(eval_string):
        args = __secure_call_args__()
        return eval(eval_string, __secure_call_globals__, args)
    else:
        return Exception("There is a syntax error, please enter the expression according to the safety standard")


def secure_call_exec(eval_string: str):
    if __check_shield__(eval_string):
        args = __secure_call_args__()
        return exec(eval_string, __secure_call_globals__, args)
    else:
        return Exception("There is a syntax error, please enter the expression according to the safety standard")
