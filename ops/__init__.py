import bpy

from . import export_import, switch_mode
from . import gesture
from . import restore_key
from . import set_direction
from . import set_key
from . import set_poll
from . import switch_ui
from .modal_mouse import ModalMouseOperator
from .qucik_add.create_element_operator import CreateElementOperator
from .qucik_add.create_element_property import CreateElementProperty
from .qucik_add.gesture_quick_add import GestureQuickAdd

operator_list = (
    switch_ui.SwitchGestureWindow,

    set_poll.SetPollExpression,

    set_key.OperatorSetKeyMaps,
    set_key.OperatorTempModifierKey,

    gesture.GestureOperator,
    GestureQuickAdd,

    CreateElementProperty,
    CreateElementOperator,
    ModalMouseOperator,

    export_import.Export,
    export_import.Import,

    restore_key.RestoreKey,

    set_direction.SetDirection,

    switch_mode.SwitchMode,
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)


def register():
    register_classes()


def unregister():
    unregister_classes()
