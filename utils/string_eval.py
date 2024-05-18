import ast

import bpy


def __is_enabled_addon__(addon_name):  # 测试是否启用此插件
    return addon_name in bpy.context.preferences.addons


__globals = {"__builtins__": None,
             'len': len,
             'is_enabled_addon': __is_enabled_addon__,
             'print': print
             #  'max':max,
             #  'min':min,
             }


def __poll_args():
    """反回poll eval的环境

    Returns:
        _type_: _description_
    """
    C = bpy.context
    D = bpy.data
    ob = bpy.context.object
    sel_objs = bpy.context.selected_objects
    use_sel_obj = ((not ob) and sel_objs)  # 使用选择的obj最后一个
    Object = sel_objs[-1] if use_sel_obj else ob
    mesh = Object.data if Object else None

    return {'bpy': bpy,
            'C': C,
            'D': D,
            'O': Object,
            'mode': C.mode,
            'tool': C.tool_settings,
            'mesh': mesh,
            }


__shield = {'Del',
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


def __check_shield(eval_string):
    dump_data = ast.dump(ast.parse(eval_string), indent=2)
    is_shield = {i for i in __shield if i in dump_data}
    if is_shield:
        e = Exception(f'input poll_string is invalid\t{is_shield} of {eval_string}')
        print(e)
        return e


def try_call_eval(eval_string: str):
    if __check_shield(eval_string) is not Exception:
        return eval(eval_string, __globals, __poll_args())


def try_call_exec(eval_string: str):
    if __check_shield(eval_string) is not Exception:
        return exec(eval_string, __globals, __poll_args())
