exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项
public_color = {"size": 4, "subtype": 'COLOR_GAMMA', "min": 0, "max": 1}


def is_blender_close() -> bool:
    import sys
    import traceback
    for stack in traceback.extract_stack(sys._getframe().f_back, limit=None):
        if stack.name == "disable_all" and stack.line == "disable(mod_name)":
            return True
    return False
