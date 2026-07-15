import bpy
from bpy.props import BoolProperty

from ..utils.public import get_pref


class DebugProperty(bpy.types.PropertyGroup):
    debug_mode: BoolProperty(
        name='Debug mode',
        description='Master switch for debug logging',
        default=False,
    )
    debug_key: BoolProperty(
        name='Debug key',
        description='Log keymap and pass-through key matching',
        default=False,
    )
    debug_kmi_sync: BoolProperty(
        name='Debug KMI sync',
        description='Log temporary keymap item synchronization',
        default=False,
    )
    debug_draw_gpu_mode: BoolProperty(
        name='Debug draw GPU mode',
        description='Show GPU draw debug overlays while using gestures',
        default=False,
    )
    debug_export_import: BoolProperty(
        name='Debug export import',
        description='Log export, import, and backup operations',
        default=False,
    )
    debug_operator: BoolProperty(
        name='Debug operator',
        description='Log operator element execution',
        default=False,
    )
    debug_modal: BoolProperty(
        name='Debug modal operator',
        description='Log modal operator element execution',
        default=False,
    )
    debug_poll: BoolProperty(
        name='Debug poll',
        description='Log poll / condition expression evaluation',
        default=False,
    )
    debug_cache: BoolProperty(
        name='Debug cache',
        description='Log cache invalidation and rebuild',
        default=False,
    )
    debug_extension: BoolProperty(
        name='Debug extension',
        description='Log extension menu hover and layout',
        default=False,
    )

    @staticmethod
    def draw_debug(layout: bpy.types.UILayout):
        from ..utils.public_ui import draw_extend_ui

        pref = get_pref()
        debug = pref.debug_property

        is_draw, lay = draw_extend_ui(
            layout,
            'draw_debug',
            label='Debug',
            default_extend=False,
        )
        if not is_draw:
            return

        col = lay.column(align=True)
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
