"""Process-wide session flags cleared on add-on unregister / reload."""

from __future__ import annotations


class SessionState:
    """Mutable flags that must not survive disable/reload."""

    panel_menu_adding: bool = False
    gesture_preview_active: bool = False
    gesture_menu_active: bool = False
    context_menu_from_button: bool = False

    # Dynamic EnumProperty for CreateSwitchPanel (items callback cannot use instance attrs).
    switch_panel_by_space: dict = {}
    switch_panel_enum_items: list = [('VIEW_3D', '3D View', '')]

    @classmethod
    def clear(cls) -> None:
        try:
            from ..gesture.menu import GestureMenuRuntime

            GestureMenuRuntime.force_close_all()
        except (ImportError, RuntimeError):
            ...
        cls.panel_menu_adding = False
        cls.gesture_preview_active = False
        cls.gesture_menu_active = False
        cls.context_menu_from_button = False
        cls.switch_panel_by_space = {}
        cls.switch_panel_enum_items = [('VIEW_3D', '3D View', '')]
