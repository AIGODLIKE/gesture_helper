import ast
import re

import bpy


def get_ui_region(area: bpy.types.Area) -> tuple[bpy.types.Region | None, int]:
    """Return the N-panel (UI) region and its index within *area*."""
    if area is None:
        return None, -1
    for index, region in enumerate(area.regions):
        if region.type == 'UI':
            return region, index
    return None, -1


def get_ui_panel_categories(context) -> list[str]:
    """Read available N-panel tab names from the current area's UI region."""
    area = context.area
    if area is None:
        return []
    ui_region, _ = get_ui_region(area)
    if ui_region is None:
        return []
    try:
        ui_region.active_panel_category = ""
    except TypeError as e:
        matches = re.findall(r'\(([^()]*)\)', e.args[-1])
        if not matches:
            return []
        return list(ast.literal_eval(f"({matches[-1]})"))
    except (AttributeError, RuntimeError, ValueError):
        return []


def get_all_panels(context, check_poll=True) -> dict[str, dict[str, list]]:
    """get all panels_data

    None TOPBAR HEADER
    Gesture VIEW_3D UI
    MP7 VIEW_3D UI
    MP7 PROPERTIES WINDOW
    """
    panels_data = {}
    area = context.area.type
    region = context.region.type

    for panel in bpy.types.Panel.__subclasses__():
        category = getattr(panel, "bl_category", None)
        if category:
            if panel.bl_space_type not in panels_data:
                panels_data[panel.bl_space_type] = {}
            if panel.bl_region_type not in panels_data[panel.bl_space_type]:
                panels_data[panel.bl_space_type][panel.bl_region_type] = []
            if category not in panels_data[panel.bl_space_type][panel.bl_region_type]:
                if check_poll and panel.bl_space_type == area and panel.bl_region_type == region:
                    if not panel.poll(context):
                        continue
                panels_data[panel.bl_space_type][panel.bl_region_type].append(category)
    return panels_data


def get_panels_by_context(context, area=None, region=None, check_poll=True):
    """Get panel category from context."""
    if area is None:
        area = context.area.type
    if region is None:
        region = context.region.type
    panels = get_all_panels(context, check_poll=check_poll)
    if area in panels:
        if region in panels[area]:
            return panels[area][region]
    return []


def get_3d_panels_by_context(context):
    """Backward-compatible alias; works in any editor with an N-panel."""
    return get_ui_panel_categories(context)
