import bpy


def _get_blender_icon(icon_style):
    """Return icon name pair

    Args:
        icon_style: icon style or custom (str, str) pair. Defaults to TRIA/ARROW/TRI.
    Returns:
        (str,str): _description_
    """
    icon_data = {
        'TRI': ('DISCLOSURE_TRI_DOWN', 'DISCLOSURE_TRI_RIGHT'),
        'TRIA': ('TRIA_DOWN', 'TRIA_RIGHT'),
        'SORT': ('SORT_ASC', 'SORT_DESC'),
        'ARROW': ('DOWNARROW_HLT', 'RIGHTARROW'),
        'CHECKBOX': ('CHECKBOX_HLT', 'CHECKBOX_DEHLT'),
        'RESTRICT_SELECT': ('RESTRICT_SELECT_OFF', 'RESTRICT_SELECT_ON'),
        'HIDE': ('HIDE_OFF', 'HIDE_ON'),
        'ALIGN': ('ALIGN_LEFT', 'ALIGN_RIGHT'),
    }
    if icon_style in icon_data:
        return icon_data[icon_style]
    else:
        return icon_data['TRI']


def icon_two(bool_prop, style='CHECKBOX', custom_icon: tuple[str, str] = None, ) -> str:
    """Return icon id string from bool value
    Args:
        bool_prop (_type_): _description_
        custom_icon (tuple[str, str], optional): custom icons; True returns first. Defaults to None.
        style (str, optional): icon style. Defaults to 'CHECKBOX'.
    Returns:
        str: icon identifier
    """
    icon_true, icon_false = custom_icon if custom_icon else _get_blender_icon(style)
    return icon_true if bool_prop else icon_false


def draw_extend_ui(layout: bpy.types.UILayout, prop_name, label: str = None, align=True, alignment='LEFT',
                   default_extend=False,
                   style='BOX', icon_style='ARROW', draw_func=None, draw_func_data=None):
    """Store transient expand/collapse state on window_manager."""
    from ..props import TempDrawProperty

    extend = TempDrawProperty.temp_wm_prop()
    if extend is None:
        if label:
            layout.label(text=label)
        return False, layout

    extend_prop_name = prop_name + '_extend'
    extend_bool = getattr(extend, extend_prop_name, None)
    if not isinstance(extend_bool, bool):
        extend.default_bool_value = default_extend
        extend.add_ui_extend_bool_property = extend_prop_name
        extend_bool = getattr(extend, extend_prop_name)

    icon = icon_two(extend_bool, style=icon_style)

    lay = layout.column()
    if style == 'BOX':
        if extend_bool:
            col = layout.column(align=True)
            lay = col.box()
        else:
            col = layout
    else:
        col = lay = layout

    row = lay.row(align=align)

    row.alignment = alignment
    row.prop(extend, extend_prop_name,
             icon=icon,
             text='',
             toggle=1,
             icon_only=True,
             emboss=False
             )

    if draw_func:
        draw_func(layout=row, **draw_func_data)
    else:
        row.prop(extend, extend_prop_name,
                 text=label if label else extend_prop_name,
                 toggle=1,
                 expand=True,
                 emboss=False
                 )

    if style == 'BOX':
        if extend_bool:
            out_lay = col.column(align=True).box()
        else:
            out_lay = lay

    else:
        out_lay = lay

    return extend_bool, out_lay
