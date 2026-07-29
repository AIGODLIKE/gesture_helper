"""Process-wide session flags cleared on add-on unregister / reload."""

from __future__ import annotations


class SessionState:
    """Mutable flags that must not survive disable/reload."""

    panel_menu_adding: bool = False
    gesture_preview_active: bool = False
    gesture_preview_scope: str = ''
    gesture_preview_instance = None
    gesture_menu_active: bool = False
    context_menu_from_button: bool = False

    # Dynamic EnumProperty for CreateSwitchPanel (items callback cannot use instance attrs).
    switch_panel_by_space: dict = {}
    switch_panel_enum_items: list = [('VIEW_3D', '3D View', '')]

    @classmethod
    def begin_gesture_preview(cls, instance, scope: str) -> bool:
        """Register the single process-wide preview owner."""
        current = cls.gesture_preview_instance
        if current is not None and current is not instance:
            return False
        cls.gesture_preview_instance = instance
        cls.gesture_preview_scope = scope
        cls.gesture_preview_active = True
        return True

    @classmethod
    def end_gesture_preview(cls, instance) -> None:
        """Release preview state without clearing a newer owner."""
        if cls.gesture_preview_instance is not instance:
            return
        cls.gesture_preview_instance = None
        cls.gesture_preview_scope = ''
        cls.gesture_preview_active = False

    @classmethod
    def request_gesture_preview_close(cls) -> bool:
        """Ask the active modal preview to finish through its normal path."""
        instance = cls.gesture_preview_instance
        if instance is None:
            return False
        request_close = getattr(instance, '_request_preview_close', None)
        if not callable(request_close):
            return False
        request_close()
        return True

    @classmethod
    def clear(cls) -> None:
        try:
            from ..gesture.menu import GestureMenuRuntime

            GestureMenuRuntime.force_close_all()
        except (ImportError, RuntimeError):
            ...
        preview = cls.gesture_preview_instance
        if preview is not None:
            cleanup = getattr(preview, '_force_preview_cleanup', None)
            if callable(cleanup):
                try:
                    cleanup()
                except (AttributeError, ReferenceError, RuntimeError):
                    ...
        cls.panel_menu_adding = False
        cls.gesture_preview_active = False
        cls.gesture_preview_scope = ''
        cls.gesture_preview_instance = None
        cls.gesture_menu_active = False
        cls.context_menu_from_button = False
        cls.switch_panel_by_space = {}
        cls.switch_panel_enum_items = [('VIEW_3D', '3D View', '')]
