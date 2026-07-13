from ..utils.rna_register import register_classes_safe, unregister_classes_safe
from . import element_modal
from . import export_import, switch_mode
from . import gesture
from . import restore_key
from . import select_icon
from . import set_direction
from . import set_key
from . import set_poll
from .modal_mouse import ModalMouseOperator
from .clear_edge_properties import ClearAllEdgeProperties
from .quick_add.create_element_operator import CreateElementOperator
from .quick_add.create_element_property import CreateElementProperty
from .quick_add.create_panel_menu import CreatePanelMenu
from .quick_add.create_switch_panel import CreateSwitchPanel
from .quick_add.switch_panel_category import GestureSwitchPanelCategory
from .quick_add.gesture_preview import GesturePreview

operator_list = (
    select_icon.SelectIcon,
    select_icon.RefreshIcons,
    select_icon.OpenCustomIconFolder,
    select_icon.ClearHistory,

    element_modal.ElementModal,

    set_poll.SetPollExpression,

    set_key.OperatorSetKeyMaps,
    set_key.OperatorTempModifierKey,

    gesture.GestureOperator,
    GesturePreview,

    CreateElementProperty,
    CreateElementOperator,
    CreatePanelMenu,
    CreateSwitchPanel,
    GestureSwitchPanelCategory,

    ModalMouseOperator,
    ClearAllEdgeProperties,

    export_import.Export,
    export_import.Import,
    export_import.ExportPreferences,
    export_import.ImportPreferences,
    export_import.SaveGesturesAndUserPref,

    restore_key.RestoreKey,

    set_direction.SetDirection,

    switch_mode.SwitchMode,
)


def register():
    register_classes_safe(operator_list)


def unregister():
    unregister_classes_safe(operator_list)
