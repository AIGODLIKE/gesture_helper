"""Independent persistent menu operator."""

from bpy.app.translations import pgettext
from bpy.props import StringProperty

from ..gesture.gesture_executor import GestureExecutor
from ..gesture.menu import GestureMenuRuntime
from ..utils.adapter import operator_setattr
from ..utils.public import PublicOperator, debug_print


class GestureMenuOperator(PublicOperator, GestureMenuRuntime):
    bl_idname = 'wm.gesture_menu'
    bl_label = 'Gesture Menu'
    bl_description = 'Open a persistent Gesture Helper menu at the mouse position'
    bl_options = {'INTERNAL'}

    gesture: StringProperty()

    @classmethod
    def poll(cls, context):
        from ..utils.pref import poll_addon_preferences

        return poll_addon_preferences(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        operator_setattr(self, '_menu_area', None)
        operator_setattr(self, '_menu_screen', None)
        operator_setattr(self, '_menu_window', None)
        operator_setattr(self, '_menu_gesture_ref', None)
        operator_setattr(self, '_menu_anchor', (0.0, 0.0))
        operator_setattr(self, '_menu_panels', [])
        operator_setattr(self, '_menu_open_path', [])
        operator_setattr(self, '_menu_hovered_row', None)
        operator_setattr(self, '_menu_layout_key', None)
        operator_setattr(self, '_menu_layout_dirty', True)
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_external_modal_active', False)
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, '_menu_draw_count', 0)
        operator_setattr(self, '_menu_last_draw_error', '')

    @staticmethod
    def _draw_error(menu, _context):
        menu.layout.label(text='Menu gesture not found', icon='ERROR')
        menu.layout.label(text='Restore or recreate its shortcut in preferences')

    def invoke(self, context, event):
        area = context.area
        if area is None or area.type in {'PREFERENCES', 'FILE_BROWSER'}:
            return {'CANCELLED'}

        from ..utils.gesture_store import get_gestures

        gestures = get_gestures()
        gesture = gestures.get(self.gesture) if gestures is not None else None
        if gesture is None or gesture.gesture_type != 'MENU':
            context.window_manager.popup_menu(
                self.__class__._draw_error,
                title=pgettext('Error'),
                icon='ERROR',
            )
            return {'CANCELLED'}

        from ..utils.public_cache import PublicCacheFunc
        from ..utils.region_mouse import mouse_in_window_region

        PublicCacheFunc.ensure_gesture_structure(gesture)
        mouse = mouse_in_window_region(event, area)
        if mouse is None:
            return {'CANCELLED'}

        operator_setattr(self, '_menu_area', area)
        operator_setattr(self, '_menu_screen', context.screen)
        operator_setattr(self, '_menu_window', context.window)
        operator_setattr(self, '_menu_gesture_ref', gesture)
        operator_setattr(self, '_menu_anchor', (mouse[0] + 6.0, mouse[1] + 6.0))
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, 'event', event)

        if not self._register_menu_runtime(context):
            return {'CANCELLED'}
        self._ensure_layout(force=True)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _area_is_live(self) -> bool:
        area = self._menu_area
        screen = self._menu_screen
        if area is None or screen is None:
            return False
        try:
            return any(candidate == area for candidate in screen.areas)
        except (AttributeError, ReferenceError, RuntimeError):
            return False

    def _has_external_modal(self, context) -> bool:
        window = self._menu_window or context.window
        if window is None:
            return False
        try:
            operators = tuple(window.modal_operators)
        except (AttributeError, ReferenceError, RuntimeError):
            return False
        for operator in operators:
            try:
                if operator == self:
                    continue
                identifier = getattr(operator, 'bl_idname', '') or type(operator).__name__
                if identifier in {'wm.gesture_menu', 'WM_OT_gesture_menu'}:
                    continue
                return True
            except ReferenceError:
                continue
        return False

    def _finish_menu(self, *, cancelled=False, pass_through=False):
        if not self._menu_runtime_cleaned:
            operator_setattr(self, '_menu_runtime_cleaned', True)
            self._unregister_menu_runtime()
        result = {'CANCELLED'} if cancelled else {'FINISHED'}
        if pass_through:
            result.add('PASS_THROUGH')
        return result

    def _execute_menu_row(self, row) -> None:
        element = row.element
        if element is None:
            return
        element.ops = self
        if row.kind == 'PROPERTY':
            GestureExecutor._run_property_element(self, element)
            self._menu_mark_context_changed()
            return
        if row.kind != 'OPERATOR':
            return
        if element.operator_func is None:
            self.report(
                {'ERROR'},
                pgettext('Operator not found: %s') % element.operator_bl_idname,
            )
            return
        if not element.check_operator_poll():
            self.report(
                {'WARNING'},
                pgettext('Operator unavailable in this context: %s') % element.operator_bl_idname,
            )
            self._menu_mark_context_changed()
            return
        try:
            error = element.running_operator()
        except Exception as exc:
            error = exc
        if error is not None:
            debug_print('Persistent menu operator error', error, key='operator')
            self.report({'ERROR'}, pgettext('Operator error. Check the console for details.'))
        else:
            self.report({'INFO'}, element.name_translate)
        self._menu_mark_context_changed()

    def modal(self, context, event):
        operator_setattr(self, 'event', event)
        if self._menu_close_requested:
            return self._finish_menu(pass_through=True)
        if not self._area_is_live() or event.type == 'WINDOW_DEACTIVATE':
            return self._finish_menu(cancelled=True)

        external_modal = self._has_external_modal(context)
        if external_modal:
            operator_setattr(self, '_menu_external_modal_active', True)
            return {'PASS_THROUGH'}
        if self._menu_external_modal_active:
            operator_setattr(self, '_menu_external_modal_active', False)
            self._menu_mark_context_changed()

        if event.value == 'PRESS' and event.type in {'ESC', 'RIGHTMOUSE'}:
            return self._finish_menu()

        if event.type == 'MOUSEMOVE':
            if self._update_menu_hover(event):
                self._tag_menu_redraw()
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._ensure_layout()
            if self._menu_close_hit(event):
                return self._finish_menu()
            row = self._menu_clicked_row(event)
            if row is not None:
                self._execute_menu_row(row)
                return {'RUNNING_MODAL'}
            if not self._menu_contains(self._menu_mouse(event)):
                return self._finish_menu(pass_through=True)
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def cancel(self, _context):
        return self._finish_menu(cancelled=True)
