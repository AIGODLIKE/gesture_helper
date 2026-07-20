public_color = {"size": 4, "subtype": 'COLOR', "min": 0, "max": 1}
import bpy


def is_blender_close() -> bool:
    """True when unregister runs as part of Blender exit (addon_utils.disable_all).

    Manual disable goes through ``addon_utils.disable`` only, without ``disable_all``.
    Blender 4.x used ``disable(mod_name)``; 5.x uses ``disable(mod_name, refresh_handled=True)``.
    Match the caller frame name instead of an exact source line.
    """
    import sys
    import traceback

    for stack in traceback.extract_stack(sys._getframe().f_back, limit=None):
        if stack.name == "disable_all":
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
