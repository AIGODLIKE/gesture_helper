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


def _iter_panel_classes():
    """Yield all Panel subclasses (including nested)."""
    stack = list(bpy.types.Panel.__subclasses__())
    seen = set()
    while stack:
        panel = stack.pop()
        if panel in seen:
            continue
        seen.add(panel)
        yield panel
        stack.extend(panel.__subclasses__())


def get_all_panels(context, check_poll=True) -> dict[str, dict[str, list]]:
    """get all panels_data

    None TOPBAR HEADER
    Gesture VIEW_3D UI
    MP7 VIEW_3D UI
    MP7 PROPERTIES WINDOW
    """
    panels_data = {}
    area = getattr(context.area, "type", None)
    region = getattr(context.region, "type", None)

    for panel in _iter_panel_classes():
        category = getattr(panel, "bl_category", None)
        if not category:
            continue
        space_type = getattr(panel, "bl_space_type", None)
        region_type = getattr(panel, "bl_region_type", None)
        if not space_type or not region_type:
            continue
        if space_type not in panels_data:
            panels_data[space_type] = {}
        if region_type not in panels_data[space_type]:
            panels_data[space_type][region_type] = []
        if category in panels_data[space_type][region_type]:
            continue
        if check_poll and space_type == area and region_type == region:
            poll = getattr(panel, "poll", None)
            if callable(poll) and not poll(context):
                continue
        panels_data[space_type][region_type].append(category)
    return panels_data


def get_panels_by_context(context, area=None, region=None, check_poll=True):
    """Get panel category from context."""
    if area is None:
        area = getattr(context.area, "type", None)
    if region is None:
        region = getattr(context.region, "type", None)
    if not area or not region:
        return []
    panels = get_all_panels(context, check_poll=check_poll)
    if area in panels:
        if region in panels[area]:
            return panels[area][region]
    return []


def get_ui_panels_by_space(context, check_poll=False) -> dict[str, list[str]]:
    """Return ``{space_type: [category, ...]}`` for every editor with N-panel tabs."""
    panels = get_all_panels(context, check_poll=check_poll)
    result = {}
    for space_type, regions in panels.items():
        ui_cats = regions.get("UI")
        if ui_cats:
            result[space_type] = list(ui_cats)
    return result


def get_all_ui_panel_categories(context, check_poll=False) -> list[str]:
    """Unique N-panel tab names across all editor types (stable order)."""
    categories = []
    seen = set()
    by_space = get_ui_panels_by_space(context, check_poll=check_poll)
    for space_type in sorted(by_space):
        for category in by_space[space_type]:
            if category not in seen:
                seen.add(category)
                categories.append(category)
    return categories


def get_3d_panels_by_context(context):
    """Backward-compatible alias; works in any editor with an N-panel."""
    cats = get_ui_panel_categories(context)
    if cats:
        return cats
    return get_all_ui_panel_categories(context)
