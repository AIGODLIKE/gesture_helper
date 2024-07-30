import bpy

from . import export_import, switch_mode
from . import gesture
from .qucik_add import gesture_quick_add
from . import restore_key
from . import set_direction
from . import set_key
from . import set_poll
from . import switch_ui

operator_list = (
    switch_ui.SwitchGestureWindow,

    set_poll.SetPollExpression,

    set_key.OperatorSetKeyMaps,
    set_key.OperatorTempModifierKey,

    gesture.GestureOperator,
    gesture_quick_add.GestureQuickAdd,

    export_import.Export,
    export_import.Import,

    restore_key.RestoreKey,

    set_direction.SetDirection,

    switch_mode.SwitchMode,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)

kc = bpy.context.window_manager.keyconfigs.addon  # 获取按键配置addon的
# km = kc.keymaps.new(name='3D View', space_type='VIEW_3D', region_type='WINDOW')
kmi = None

def register():
    register_classes()


def unregister():
    unregister_classes()
