import bpy

from . import export_import, switch_mode
from . import gesture
from . import restore_key
from . import select_icon
from . import set_direction
from . import set_key
from . import set_poll
from . import switch_ui
from .modal_mouse import ModalMouseOperator
from .qucik_add.create_element_operator import CreateElementOperator
from .qucik_add.create_element_property import CreateElementProperty
from .qucik_add.create_panel_menu import CreatePanelMenu
from .qucik_add.gesture_preview import GesturePreview

operator_list = (
    select_icon.SelectIcon,
    select_icon.RefreshIcons,

    switch_ui.SwitchGestureWindow,

    set_poll.SetPollExpression,

    set_key.OperatorSetKeyMaps,
    set_key.OperatorTempModifierKey,

    gesture.GestureOperator,
    GesturePreview,

    CreateElementProperty,
    CreateElementOperator,
    CreatePanelMenu,
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
