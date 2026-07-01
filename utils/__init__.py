import re
from functools import cache

exclude_items = {'rna_type', 'bl_idname', 'srna'}  # Excluded identifiers
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
def check_china(text):
    """Return True if text is entirely Chinese characters."""
    if not isinstance(text, str):
        return False
    return bool(re.compile(r'[\u4e00-\u9fa5]').findall(text))


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
    # Match any character that is not a letter, digit, or underscore
    pattern = r'[^A-Za-z0-9_.]'
    if re.search(pattern, input_string):
        return True
    return False


def get_region(region_type, context=None) -> "None|bpy.types.Region":
    """
    enum in ["WINDOW", "HEADER", "CHANNELS", "TEMPORARY", "UI", "TOOLS", "TOOL_PROPS",
        "PREVIEW", "HUD", "NAVIGATION_BAR", "EXECUTE", "FOOTER", "TOOL_HEADER", "XR"]]
    region_types = set(region.type for area in bpy.context.screen.areas for region in area.regions)
    {
    'WINDOW',
     'ASSET_SHELF',
     'TOOL_HEADER',
     'ASSET_SHELF_HEADER',
     'HUD',
     'UI',
     'NAVIGATION_BAR',
     'TOOLS',
     'EXECUTE',
     'HEADER',
     'CHANNELS'
     }
    """
    area = bpy.context.area if context is None else context.area
    for region in area.regions:
        if region.type == region_type:
            return region
    return None


def get_toolbar_width(region_type="TOOLS"):
    for i in bpy.context.area.regions:
        if i.type == region_type:
            if region_type == "TOOLS":
                return i.width
            elif region_type in ("HEADER", "TOOL_HEADER"):
                return i.height
    return None


def get_region_height(context, region_type="TOOLS") -> int:
    if area := get_region(region_type, context):
        return area.height
    return 0


def get_region_width(context, region_type="TOOLS") -> int:
    if area := get_region(region_type, context):
        return area.width
    return 0
