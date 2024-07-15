import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup

from ..utils import isDebug
from ..utils.public import get_pref


class DebugProperty(PropertyGroup):
    debug_mode: BoolProperty(name='Debug模式', default=isDebug)
    debug_key: BoolProperty(name='Debug快捷键', default=isDebug)
    debug_draw_gpu_mode: BoolProperty(name='Debug绘制Gpu模式', default=isDebug)
    debug_export_import: BoolProperty(name='Debug导入导出', default=isDebug)
    debug_poll: BoolProperty(name='Debug Poll', default=isDebug)

    @staticmethod
    def draw_debug(layout: bpy.types.UILayout):
        """
        绘制Debug属性
        :param layout:
        :return:
        """
        pref = get_pref()
        debug = pref.debug_property

        col = layout.box().column(heading="Debug", align=True)

        ops = col.operator("preferences.keymap_restore")
        ops.all = True
        col.prop(debug, 'debug_mode')
        col.prop(debug, 'debug_key')
        col.prop(debug, 'debug_draw_gpu_mode')
        col.prop(debug, 'debug_export_import')
        col.prop(debug, 'debug_poll')
