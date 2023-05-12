import bpy
from bpy.props import BoolProperty
from bpy_types import Operator

from .public_data import PublicData


class PublicUi:

    @staticmethod
    def _get_blender_icon(icon_style):
        """反回图标名称

        Args:
            icon_style (类型或直接输入两个已设置的图标, optional): 图标风格,也可以自已设置图标id. Defaults to 'TRIA' | 'ARROW' | 'TRI' | (str, str).
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
        }
        if icon_style in icon_data:
            return icon_data[icon_style]
        else:
            return icon_data['TRI']

    @staticmethod
    def icon_two(bool_prop, style='CHECKBOX', custom_icon: tuple[str, str] = None, ) -> str:
        """输入一个布尔值,反回图标类型str
        Args:
            bool_prop (_type_): _description_
            custom_icon (tuple[str, str], optional): 输入两个自定义的图标名称,True反回前者. Defaults to None.
            style (str, optional): 图标的风格. Defaults to 'CHECKBOX'.
        Returns:
            str: 反回图标str
        """
        icon_true, icon_false = custom_icon if custom_icon else PublicUi._get_blender_icon(
            style)
        return icon_true if bool_prop else icon_false

    @staticmethod
    def space_layout(layout: 'bpy.types.UILayout', space: int, level: int) -> 'bpy.types.UILayout':
        """
        设置间隔
        """
        if level == 0:
            return layout.column()
        indent = level * space / bpy.context.region.width

        split = layout.split(factor=indent)
        split.column()
        return split.column()

    @staticmethod
    def draw_default_ui_list_filter(ui_list, layout):
        """绘制UIList默认过滤UI"""
        sub_row = layout.row(align=True)
        sub_row.prop(ui_list, 'filter_name')
        sub_row.prop(ui_list, 'use_filter_invert',
                     icon='ARROW_LEFTRIGHT',
                     toggle=True,
                     icon_only=True,
                     )
        if not (ui_list.use_filter_sort_lock and ui_list.bitflag_filter_item):
            sub = sub_row.row(align=True)
            sub.prop(ui_list, 'use_filter_sort_alpha',
                     toggle=True,
                     icon_only=True,
                     )
            icon = 'SORT_REVERSE' if (
                    ui_list.bitflag_filter_item and ui_list.use_filter_sort_reverse) else 'SORT_ASC'
            sub.prop(ui_list, 'use_filter_sort_reverse',
                     icon=icon,
                     toggle=True,
                     icon_only=True,
                     )


class PublicPopupMenu(Operator):
    title: str
    bl_label: str
    bl_idname: str
    is_popup_menu: BoolProperty(name='弹出菜单',
                                description='''是否为弹出菜单,如果为True则弹出菜单,''',
                                default=True,
                                **PublicData.PROP_DEFAULT_SKIP,
                                )

    def execute(self, context):
        print(self.bl_label)
        return {'FINISHED'}

    def draw_menu(self, menu, context):
        layout = menu.layout
        layout.label(text=self.bl_label)
        ops = layout.operator(self.bl_idname)
        ops.is_popup_menu = False

    def invoke(self, context, event):
        if self.is_popup_menu:
            context.window_manager.popup_menu(
                self.draw_menu, title=getattr(self, 'title', self.bl_label))
            return {'FINISHED'}
        return self.execute(context)
