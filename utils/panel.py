import bpy


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


if __name__ == "__main__":
    print(get_all_panels(bpy.context))
