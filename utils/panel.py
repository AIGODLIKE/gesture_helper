import bpy
import re
import ast


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
    """通过上下文获取面板的分类"""
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
    """
  File "<string>", line 1, in <module>
TypeError: bpy_struct: item.attr = val: enum "glTF Variants" not found in ('Item', 'Tool', 'View', 'MP7', 'Gesture')
    """
    try:
        context.area.regions[5].active_panel_category = ""
    except TypeError as e:
        matches = re.findall(r'\(([^()]*)\)', e.args[-1])
        return ast.literal_eval(f"({matches[-1]})")


if __name__ == "__main__":
    print(get_all_panels(bpy.context))
