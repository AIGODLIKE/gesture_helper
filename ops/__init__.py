import bpy.utils

from . import switch_ui
from . import key
from . import gesture

operator_list = (
    switch_ui.SwitchGestureWindow,

    key.OperatorSetKeyMaps,
    key.OperatorTempModifierKey,

    gesture.GestureOperator
)

reg, un_reg = bpy.utils.register_classes_factory(operator_list)


def register():
    reg()


def unregister():
    un_reg()
