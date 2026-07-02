import bpy
from bpy.props import BoolProperty

from ..utils.public import get_pref


class DebugProperty(bpy.types.PropertyGroup):
    debug_mode: BoolProperty(name='Debug mode', default=False)
    debug_key: BoolProperty(name='Debug key', default=False)
    debug_kmi_sync: BoolProperty(name='Debug KMI sync', default=False)
    debug_draw_gpu_mode: BoolProperty(name='Debug draw gpu mode', default=False)
    debug_export_import: BoolProperty(name='Debug export import', default=False)
    debug_operator: BoolProperty(name='Debug operator', default=False)
    debug_modal: BoolProperty(name='Debug modal operator', default=False)
    debug_poll: BoolProperty(name='Debug Poll', default=False)
    debug_cache: BoolProperty(name='Debug cache', default=False)
    debug_extension: BoolProperty(name='Debug Extension', default=False)

    @staticmethod
    def draw_debug(layout: bpy.types.UILayout):
        pref = get_pref()
        debug = pref.debug_property

        col = layout.box().column(heading="Debug", align=True)
        col.prop(debug, 'debug_mode')
        col.prop(debug, 'debug_key')
        col.prop(debug, 'debug_kmi_sync')
        col.prop(debug, 'debug_draw_gpu_mode')
        col.prop(debug, 'debug_export_import')
        col.prop(debug, 'debug_operator')
        col.prop(debug, 'debug_modal')
        col.prop(debug, 'debug_poll')
        col.prop(debug, 'debug_cache')
        col.prop(debug, 'debug_extension')
