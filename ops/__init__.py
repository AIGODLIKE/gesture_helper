import bpy

from . import gesture
from . import set_key
from . import switch_ui

operator_list = (
    switch_ui.SwitchGestureWindow,

    set_key.OperatorSetKeyMaps,
    set_key.OperatorTempModifierKey,

    gesture.GestureOperator
)

register_classes, unregister_classes = bpy.utils.register_classes_factory(operator_list)


def register():
    register_classes()


def unregister():
    unregister_classes()
