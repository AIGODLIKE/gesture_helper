import re
from functools import cache

public_color = {"size": 4, "subtype": 'COLOR', "min": 0, "max": 1}
import bpy


def is_blender_close() -> bool:
    import sys
    import traceback
    for stack in traceback.extract_stack(sys._getframe().f_back, limit=None):
        if stack.name == "disable_all" and stack.line == "disable(mod_name)":
            return True
    return False


@cache
def including_chinese(text) -> bool:
    """Return True if text contains any Chinese characters."""
    if not isinstance(text, str):
        return False
    return bool(re.compile(r'[\u4e00-\u9fff]+').search(text))


@cache
def contains_uppercase(s) -> bool:
    """Return True if text contains any uppercase letter."""
    return any(char.isupper() for char in s)


@cache
def has_special_characters(input_string):
    """
    Check whether the string contains characters other than letters, digits, and underscores.

    Args:
    input_string (str): String to check.

    Returns:
    bool: True if non-alphanumeric/underscore characters are present, else False.
    """
    pattern = r'[^A-Za-z0-9_.]'
    if re.search(pattern, input_string):
        return True
    return False


def get_region(region_type, context=None) -> "None|bpy.types.Region":
    ctx = bpy.context if context is None else context
    area = getattr(ctx, 'area', None)
    if area is None:
        return None
    for region in area.regions:
        if region.type == region_type:
            return region
    return None


def get_region_height(context, region_type="TOOLS") -> int:
    if area := get_region(region_type, context):
        return area.height
    return 0


def get_region_width(context, region_type="TOOLS") -> int:
    if area := get_region(region_type, context):
        return area.width
    return 0
