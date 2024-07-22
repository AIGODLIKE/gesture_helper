import os

import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty
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
    backups_file_mode:EnumProperty(
        name="备份模式",
        default="ADDON_UNREGISTER_DAY",
        items=[
            ("ADDON_UNREGISTER", "插件注销时", "每次插件注销时都会自动备份一次(在关闭插件或关闭Blender时会触发),如果频繁开关Blender将会有很多备份文件"),
            ("ADDON_UNREGISTER_DAY", "插件注销时(每天保留一份)", "每天仅保留一份"),
            ("ONLY_ONE", "仅保留一份", "仅保留一份")
        ]
    )

    @staticmethod
    def draw_backups(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        backups = pref.backups_property
        column = layout.column(heading="Auto Backups")

        box = column.box()
        box.prop(backups, 'auto_backups')
        box.prop(backups, 'backups_file_mode')
        box.prop(backups, 'enabled_backups_to_specified_path')
        if backups.enabled_backups_to_specified_path:
            box.prop(backups, 'backups_path')

        # if backups.auto_backups:
        # else:
        #     column.prop(backups, 'auto_backups')
