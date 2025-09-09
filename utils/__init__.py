import re
from functools import cache

exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项
public_color = {"size": 4, "subtype": 'COLOR', "min": 0, "max": 1}


def is_blender_close() -> bool:
    import sys
    import traceback
    for stack in traceback.extract_stack(sys._getframe().f_back, limit=None):
        if stack.name == "disable_all" and stack.line == "disable(mod_name)":
            return True
    return False


@cache
def check_china(text):
    """全部是中文"""
    if not isinstance(text, str):
        return False
    return bool(re.compile(r'[\u4e00-\u9fa5]').findall(text))


@cache
def including_chinese(text) -> bool:
    """包含中文"""
    if not isinstance(text, str):
        return False
    return bool(re.compile(r'[\u4e00-\u9fff]+').search(text))


@cache
def has_special_characters(input_string):
    """
    检查字符串是否包含字母、数字和下划线之外的字符

    参数:
    input_string (str): 要检查的字符串

    返回:
    bool: 如果包含非字母数字和下划线字符返回True，否则返回False
    """
    # 使用正则表达式匹配任何非字母、数字或下划线的字符
    pattern = r'[^A-Za-z0-9_.]'
    if re.search(pattern, input_string):
        return True
    return False
