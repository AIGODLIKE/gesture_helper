import bpy
from bpy.props import BoolProperty

from ..debug import IS_DEBUG
from ..utils.public import get_pref


class DebugProperty(bpy.types.PropertyGroup):
    debug_mode: BoolProperty(name='Debug mode', default=IS_DEBUG)
    debug_key: BoolProperty(name='Debug key', default=IS_DEBUG)
    debug_draw_gpu_mode: BoolProperty(name='Debug draw gpu mode', default=IS_DEBUG)
    debug_export_import: BoolProperty(name='Debug export import', default=IS_DEBUG)
    debug_operator: BoolProperty(name='Debug operator', default=False)
    debug_poll: BoolProperty(name='Debug Poll', default=False)
    debug_extension: BoolProperty(name='Debug Extension', default=False)

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
        col.prop(debug, 'debug_operator')
        col.prop(debug, 'debug_poll')
        col.prop(debug, 'debug_extension')
