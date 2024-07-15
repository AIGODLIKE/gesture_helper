import os

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup


class BackupsProperty(PropertyGroup):
    from ..utils.public import ADDON_FOLDER
    auto_backups: BoolProperty(
        name='启用自动备份',
        description='在每次注销插件时自动保存数据,避免误操作导致数据丢失, 自动保存的路径在插件路径的 "auto_backups" 文件夹',
        default=True,
    )
    enabled_backups_to_specified_path: BoolProperty(
        name='指定备份路径',
        description='备份到指定路径',
        default=False,
    )
    backups_path: StringProperty(
        name='备份路径',
        description='备份配置到指定路径',
        subtype='DIR_PATH',
        default=os.path.join(ADDON_FOLDER, 'auto_backups')
    )

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        other = pref.other_property
        column = layout.column(heading="Auto Backups")

        box = column.box()
        box.prop(other, 'auto_backups')
        box.prop(other, 'enabled_backups_to_specified_path')
        if other.enabled_backups_to_specified_path:
            box.prop(other, 'backups_path')

        # if other.auto_backups:
        # else:
        #     column.prop(other, 'auto_backups')
